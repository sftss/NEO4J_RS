import random, json, math
from collections import defaultdict
from datetime import datetime, timedelta
from faker import Faker
import networkx as nx

# Reproductibilité
SEED = 42
random.seed(SEED); Faker.seed(SEED)
fake = Faker("fr_FR")

# Cibles
N_USERS = 3000
TARGET_FOLLOWS = 5000          # relations dirigées
TARGET_POSTS = 1000
TARGET_LIKES = 1500
TARGET_COMMENTS = 900
DAYS = 60                      # fenêtre temporelle d'activité

# Communautés "classiques"
COMMUNITIES = [
    {"id":"jeux_video", "tags":["gaming","esport","pc","console","rpg","fps"]},
    {"id":"animaux",    "tags":["chien","chat","faune","soin","refuge","adoption"]},
    {"id":"evenements", "tags":["festival","concert","salon","conférence","expo","after"]},
    {"id":"musique",    "tags":["rock","pop","rap","jazz","playlist","live"]},
    {"id":"sport",      "tags":["foot","running","velo","fitness","match","tournoi"]},
    {"id":"voyage",     "tags":["europe","montagne","plage","citytrip","hôtel","train"]},
]

N_COMM = len(COMMUNITIES)

# Helpers
def ndt(start_days=60):
    start = datetime.utcnow() - timedelta(days=start_days)
    t = start + timedelta(days=random.random()*start_days, hours=random.randint(7,23), minutes=random.randint(0,59))
    return t.replace(microsecond=0).isoformat()

# 1) Users
users = []
for i in range(N_USERS):
    c = COMMUNITIES[i % N_COMM]
    users.append({
        "id": f"u_{i:05d}",
        "username": fake.user_name(),
        "createdAt": fake.date_time_between(start_date="-1y", end_date="-5d").isoformat(),
        "community": c["id"]
    })

cid_by_user = {u["id"]: u["community"] for u in users}

# Follows (préférential + quota exact)
# génère un graphe BA léger pour une distribution
G = nx.barabasi_albert_graph(N_USERS, 1, seed=SEED)  # m=1 => très épars
# puis échantillonne des paires avec biais "même communauté"
edges_dir = set()
deg_pref = defaultdict(int)
def try_add(a,b):
    if a==b or (a,b) in edges_dir: return False
    edges_dir.add((a,b))
    deg_pref[b]+=1
    return True

# amorce avec quelques arêtes du BA (dirigées aléatoirement)
for (a,b) in G.edges():
    if len(edges_dir) >= TARGET_FOLLOWS: break
    if random.random() < 0.5: try_add(a,b)
    else: try_add(b,a)

# complétion jusqu'à TARGET_FOLLOWS avec biais intra-communauté + préférential attach
while len(edges_dir) < TARGET_FOLLOWS:
    a = random.randrange(N_USERS)
    # cible b: soit même communauté (proba 0.7), sinon autre
    same = random.random() < 0.7
    pool = range(N_USERS)
    # tirage préférentiel sur la popularité (deg_pref)
    # score = 1 + deg_pref[b] + bonus si même communauté
    best = None; best_score = -1
    trials = 20
    for _ in range(trials):
        b = random.randrange(N_USERS)
        if a==b: continue
        if same and (users[a]["community"] != users[b]["community"]): continue
        score = 1 + deg_pref[b] + (2 if cid_by_user[f"u_{b:05d}"]==cid_by_user[f"u_{a:05d}"] else 0)
        if score > best_score and (a,b) not in edges_dir:
            best, best_score = (a,b), score
    if best:
        try_add(*best)

follows = [{"src": f"u_{a:05d}", "dst": f"u_{b:05d}", "since": ndt(DAYS)} for (a,b) in edges_dir]

# Posts répartition sur les users, biais communauté vers son topic
# On répartit TARGET_POSTS proportionnellement à (1 + sqrt(in-degree))
in_deg = defaultdict(int)
for _,b in edges_dir: in_deg[b]+=1
weights = [1 + math.sqrt(in_deg[i]) for i in range(N_USERS)]
total_w = sum(weights)
quota = [0]*N_USERS
remaining = TARGET_POSTS
for i in range(N_USERS-1):
    qi = int(round(remaining * (weights[i]/total_w)))
    quota[i] = qi
    remaining -= qi
quota[-1] += remaining  

posts, post_tags = [], []
pid = 0
for i, q in enumerate(quota):
    if q <= 0: continue
    author = users[i]
    topic = f"topic_{author['community']}"
    for _ in range(q):
        pid += 1
        p_id = f"p_{pid:06d}"
        posts.append({"id": p_id, "authorId": author["id"], "createdAt": ndt(DAYS), "topic": topic})
        # 1 à 3 tags
        k = random.randint(1,3)
        chosen = random.sample(next(c["tags"] for c in COMMUNITIES if c["id"]==author["community"]), k)
        for t in chosen:
            post_tags.append({"postId": p_id, "tag": t})

# Likes ≈ TARGET_LIKES, pas de doublon user->post, pas d'auto-like
likes = []
liked_pairs = set()
all_users = [u["id"] for u in users]
for _ in range(TARGET_LIKES):
    p = random.choice(posts)
    # favorise même communauté que l'auteur
    author_c = cid_by_user[p["authorId"]]
    for _ in range(30):
        v = random.choice(all_users)
        if v == p["authorId"]: continue
        if (v, p["id"]) in liked_pairs: continue
        same = (cid_by_user[v] == author_c)
        if random.random() < (0.7 if same else 0.3):
            liked_pairs.add((v, p["id"]))
            likes.append({"userId": v, "postId": p["id"], "createdAt": p["createdAt"]})
            break

# Comments ≈ TARGET_COMMENTS
comments = []
for i in range(TARGET_COMMENTS):
    p = random.choice(posts)
    # comment
    for _ in range(30):
        v = random.choice(all_users)
        if v == p["authorId"] and random.random() < 0.6:
            continue  # limite auto-comment
        comments.append({
            "id": f"c_{i+1:07d}",
            "authorId": v,
            "postId": p["id"],
            "createdAt": p["createdAt"],
            "text": fake.sentence(nb_words=12)
        })
        break

# Export .ndjson
def dump_ndjson(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

dump_ndjson("data/users.ndjson", users)
dump_ndjson("data/follows.ndjson", follows)
dump_ndjson("data/posts.ndjson", posts)
dump_ndjson("data/post_tags.ndjson", post_tags)
dump_ndjson("data/likes.ndjson", likes)
dump_ndjson("data/comments.ndjson", comments)

print("Done.",
      "users:", len(users),
      "follows:", len(follows),
      "posts:", len(posts),
      "likes:", len(likes),
      "comments:", len(comments))

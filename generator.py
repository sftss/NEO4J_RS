import random, json, math
from collections import defaultdict
from faker import Faker
from datetime import datetime, timedelta

fake = Faker("fr_FR")
Faker.seed(42)
random.seed(42)

# ============================================
# PARAMÈTRES POUR INSERTIONS
# ============================================
N_USERS = 3000
TARGET_POSTS = 5000
TARGET_LIKES = 15000
TARGET_COMMENTS = 8000
N_GROUPS = 50
N_REPORTS = 200
DAYS = 365

# Communautés avec sujets et tags
COMMUNITIES = [
    {"id": "tech",   "tags": ["ia", "python", "dev", "cloud", "api"]},
    {"id": "sport",  "tags": ["running", "fitness", "yoga", "football", "natation"]},
    {"id": "gaming", "tags": ["fps", "rpg", "esport", "console", "pc"]},
    {"id": "cuisine","tags": ["recette", "veggie", "dessert", "chef", "restaurant"]},
    {"id": "voyage", "tags": ["montagne", "plage", "roadtrip", "backpack", "citytrip"]},
]
N_COMM = len(COMMUNITIES)

# NEW: répartitions inégales des communautés (tech et sport plus grosses)
COMMUNITY_WEIGHTS = [0.35, 0.25, 0.20, 0.12, 0.08]

# compte : 55% privés, 45% publique
PRIVACY_OPTIONS = ["private", "public"]
PRIVACY_WEIGHTS = [0.55, 0.45]

# Visibilité pour posts : 60% public, 30% followers_only, 10% private
POST_VISIBILITY_OPTIONS = ["public", "followers_only", "private"]
POST_VISIBILITY_WEIGHTS = [0.6, 0.3, 0.1]

# Raisons pour reports
REPORT_REASONS = ["spam", "hate_speech", "harassment", "fake_news", "inappropriate_content"]
REPORT_STATUS = ["open", "in_review", "resolved", "dismissed"]

# NEW: paramètres "pics"
INFLUENCER_RATIO = 0.06     # ~6% d'influenceurs (pics de follows)
POST_SPIKE_RATIO = 0.08     # ~8% d'auteurs publient davantage
LIKE_MAGNET_RATIO = 0.06    # ~6% d'auteurs reçoivent beaucoup plus de likes
POST_SPIKE_FACTOR = 2.0     # multiplicateur de posts
LIKE_TARGET_FACTOR = 3.0    # multiplicateur de probabilité d'être liké
INFLUENCER_FOLLOW_BOOST = (1, 3)  # chaque user suit 1..3 influenceurs (essais)

# ============================================
# FONCTIONS
# ============================================
def ndt(days_avant):
    """Génère une date aléatoire dans les X derniers jours"""
    delta = timedelta(days=random.randint(0, days_avant))
    dt = datetime.now() - delta
    return dt.isoformat(timespec='seconds')

def random_media_url():
    """Génère une URL"""
    if random.random() < 0.3:  # 30% de posts sans média
        return None
    hash_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=12))
    extensions = ['jpg', 'png', 'mp4', 'gif']
    ext = random.choice(extensions)
    return f"https://cdn.socialnet.com/media/{hash_id}.{ext}"

def dump_ndjson(path, rows):
    """Sauvegarde en NDJSON"""
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

# ============================================
# GÉNÉRATION USERS
# ============================================
print("Génération users")
users = []
cid_by_user = {}

for i in range(N_USERS):
    # NEW: assignation pondérée aux communautés (au lieu de i % N_COMM)
    c = random.choices(COMMUNITIES, weights=COMMUNITY_WEIGHTS, k=1)[0]
    user_id = f"u_{i:05d}"
    users.append({
        "id": user_id,
        "username": fake.user_name(),
        "name": fake.name(),
        "privacy": random.choices(PRIVACY_OPTIONS, PRIVACY_WEIGHTS)[0],
        "createdAt": ndt(DAYS),
        "community": c["id"]
    })
    cid_by_user[user_id] = c["id"]

# NEW: mappages utiles + sets "pics"
id2idx = {u["id"]: i for i, u in enumerate(users)}
influencers = set(random.sample(range(N_USERS), max(1, int(N_USERS * INFLUENCER_RATIO))))
post_spikers = set(random.sample(range(N_USERS), max(1, int(N_USERS * POST_SPIKE_RATIO))))
like_magnets = set(random.sample(range(N_USERS), max(1, int(N_USERS * LIKE_MAGNET_RATIO))))

# ============================================
# GÉNÉRATION FOLLOWS
# ============================================
print("Génération des relations FOLLOWS")
edges_dir = []
neighbors_out = defaultdict(set)
neighbors_in = defaultdict(set)

def try_add(a, b):
    if a != b and b not in neighbors_out[a]:
        edges_dir.append((a, b))
        neighbors_out[a].add(b)
        neighbors_in[b].add(a)

# C=communautés importantes (intra)
for c in COMMUNITIES:
    members = [i for i in range(N_USERS) if users[i]["community"] == c["id"]]
    k = min(len(members), 15)
    for a in members:
        for b in random.sample(members, k):
            try_add(a, b)

# F=follows intercommunautés
for _ in range(N_USERS * 2):
    a, b = random.sample(range(N_USERS), 2)
    if cid_by_user[users[a]["id"]] == cid_by_user[users[b]["id"]]:
        continue
    try_add(a, b)

# NEW: boost vers influenceurs (pics de follows)
infl_list = list(influencers)
for a in range(N_USERS):
    k = random.randint(*INFLUENCER_FOLLOW_BOOST)
    for b in random.sample(infl_list, min(k, len(infl_list))):
        if random.random() < 0.6:  # probabilité modérée pour rester réaliste
            try_add(a, b)

# attachement préférentiel (renforce les hubs existants)
for _ in range(N_USERS * 3):
    a = random.randrange(N_USERS)
    if len(neighbors_in) == 0:
        break
    best, best_score = None, -1
    for _ in range(20):
        b = random.randrange(N_USERS)
        score = len(neighbors_in[b])
        if score > best_score and b not in neighbors_out[a]:
            best, best_score = (a, b), score
    if best:
        try_add(*best)

follows = [
    {
        "followerId": f"u_{a:05d}",
        "followedId": f"u_{b:05d}",
        "since": ndt(DAYS)
    }
    for (a, b) in edges_dir
]

# ============================================
# GÉNÉRATION POSTS
# ============================================
print("Génération des posts")
in_deg = defaultdict(int)
for _, b in edges_dir:
    in_deg[b] += 1

# NEW: pics de posts pour certains auteurs (facteur multiplicatif)
weights = []
for i in range(N_USERS):
    base = 1 + math.sqrt(in_deg[i])
    if i in post_spikers:
        base *= POST_SPIKE_FACTOR
    weights.append(base)

total_w = sum(weights)
quota = [0] * N_USERS
remaining = TARGET_POSTS

for i in range(N_USERS - 1):
    qi = int(round(remaining * (weights[i] / total_w)))
    quota[i] = qi
    remaining -= qi
quota[-1] += remaining

posts, post_tags = [], []
pid = 0

for i, q in enumerate(quota):
    if q <= 0:
        continue
    author = users[i]
    topic = f"topic_{author['community']}"
    
    for _ in range(q):
        pid += 1
        p_id = f"p_{pid:06d}"
        created = ndt(DAYS)
        
        posts.append({
            "id": p_id,
            "authorId": author["id"],
            "content": fake.sentence(nb_words=20),
            "visibility": random.choices(POST_VISIBILITY_OPTIONS, POST_VISIBILITY_WEIGHTS)[0],
            "mediaUrl": random_media_url(),
            "createdAt": created,
            "topic": topic,
            "likeCount": 0,      # calculé après
            "commentCount": 0    # calculé après
        })
        
        # tags (1 à 3) - graine initiale (sera remplacée par section tags détaillée)
        k = random.randint(1, 3)
        chosen = random.sample(
            next(c["tags"] for c in COMMUNITIES if c["id"] == author["community"]),
            k
        )
        for t in chosen:
            post_tags.append({"postId": p_id, "tag": t})

# ============================================
# GÉNÉRATION POST_TAGS
# ============================================
print("Génération des tags")

# Liste tags par communauté
COMMUNITY_TAGS = {
    "tech":   ["ia", "python", "dev", "cloud", "api", "javascript", "docker", "kubernetes", "react", "nodejs"],
    "sport":  ["running", "fitness", "yoga", "football", "natation", "cyclisme", "musculation", "marathon", "crossfit", "nutrition"],
    "gaming": ["fps", "rpg", "esport", "console", "pc", "streaming", "mmo", "indie", "multiplayer", "vr"],
    "cuisine":["recette", "veggie", "dessert", "chef", "restaurant", "patisserie", "bio", "vegan", "gastronomie", "streetfood"],
    "voyage": ["montagne", "plage", "roadtrip", "backpack", "citytrip", "aventure", "camping", "randonnee", "photographie", "culture"]
}

# Tags populaires
GENERIC_TAGS = ["inspiration", "lifestyle", "weekend", "motivation", "friends", "family", "nature", "art", "music", "fun"]

post_tags = []

for post in posts:
    author_id = post["authorId"]
    author_community = cid_by_user[author_id]
    
    # 70% des posts ont entre 1 et 5 tags
    if random.random() < 0.7:
        num_tags = random.randint(1, 5)
        
        # 80% des tags viennent de la communauté de l'auteur
        community_tags = COMMUNITY_TAGS.get(author_community, [])
        
        selected_tags = []
        for _ in range(num_tags):
            if random.random() < 0.8 and community_tags:
                # Tag de la communauté
                tag = random.choice(community_tags)
            else:
                # Tag populaires
                tag = random.choice(GENERIC_TAGS)
            if tag not in selected_tags:
                selected_tags.append(tag)
        
        # Ajouter les tags au post
        for tag in selected_tags:
            post_tags.append({
                "postId": post["id"],
                "tagName": tag
            })

print(f"  → {len(post_tags)} associations post-tag créées")

# ============================================
# GÉNÉRATION LIKES
# ============================================
print("Génération des likes")
likes = []
liked_pairs = set()
all_users = [u["id"] for u in users]

# NEW: biais de sélection des posts à liker (pics de likes pour certains auteurs)
like_weight_by_post = []
for p in posts:
    ai = id2idx[p["authorId"]]           # index auteur
    w = 1.0
    if ai in like_magnets:
        w *= LIKE_TARGET_FACTOR          # auteurs "magnets" attirent plus de likes
    if ai in influencers:
        w *= 1.5                         # les influenceurs aussi
    like_weight_by_post.append(w)

for _ in range(TARGET_LIKES):
    # NEW: choix du post pondéré (au lieu de uniform)
    p = random.choices(posts, weights=like_weight_by_post, k=1)[0]
    author_c = cid_by_user[p["authorId"]]

    for _ in range(30):
        v = random.choice(all_users)
        if v == p["authorId"]:
            continue
        if (v, p["id"]) in liked_pairs:
            continue

        same = (cid_by_user[v] == author_c)
        if random.random() < (0.7 if same else 0.3):
            liked_pairs.add((v, p["id"]))
            likes.append({
                "userId": v,
                "postId": p["id"],
                "likedAt": ndt(DAYS)  # timestamp aléatoire
            })
            break

# ============================================
# GÉNÉRATION COMMENTS
# ============================================
print("Génération des commentaires")
comments = []

# NEW: 30% des posts sans aucun commentaire (strict)
zero_comment_posts = set()
if len(posts) > 0:
    zero_comment_posts = set(p["id"] for p in random.sample(posts, int(0.30 * len(posts))))

for i in range(TARGET_COMMENTS):
    # choisir un post qui N'EST PAS dans zero_comment_posts
    for _ in range(20):
        p = random.choice(posts)
        if p["id"] not in zero_comment_posts:
            break
    else:
        # fallback rarissime: si tout échoue, choisir n'importe quel post commentable
        candidates = [pp for pp in posts if pp["id"] not in zero_comment_posts]
        p = random.choice(candidates) if candidates else random.choice(posts)

    for _ in range(30):
        v = random.choice(all_users)
        if v == p["authorId"] and random.random() < 0.6:
            continue

        comments.append({
            "id": f"c_{i+1:07d}",
            "authorId": v,
            "postId": p["id"],
            "createdAt": ndt(DAYS),
            "content": fake.sentence(nb_words=12)  # texte aléatoire
        })
        break

# ============================================
# CALCUL likeCount et commentCount
# ============================================
print("Calcul likeCount et commentCount")
like_count_by_post = defaultdict(int)
comment_count_by_post = defaultdict(int)

for like in likes:
    like_count_by_post[like["postId"]] += 1

for comment in comments:
    comment_count_by_post[comment["postId"]] += 1

for post in posts:
    post["likeCount"] = like_count_by_post[post["id"]]
    post["commentCount"] = comment_count_by_post[post["id"]]

# ============================================
# GÉNÉRATION GROUPS
# ============================================
print("Génération des groupes")
groups = []
group_members = []

for i in range(N_GROUPS):
    g_id = f"g_{i+1:03d}"
    community = COMMUNITIES[i % N_COMM]
    
    community_users = [u["id"] for u in users if u["community"] == community["id"]]
    creator = random.choice(community_users) if community_users else all_users[0]

    groups.append({
        "id": g_id,
        "name": f"{community['id'].capitalize()} - {fake.catch_phrase()}",
        "visibility": random.choice(["public", "private"]),
        "createdBy": creator,
        "description": fake.text(max_nb_chars=200),
        "createdAt": ndt(DAYS)
    })

    # membres du groupe (5 à 30)
    n_members = random.randint(5, 30)
    selected_members = random.sample(community_users, min(n_members, len(community_users)))

    # 1er membre = admin
    if creator not in selected_members:
        selected_members.insert(0, creator)
    
    for idx, user_id in enumerate(selected_members):
        role = "admin" if user_id == creator else (
            "moderator" if random.random() < 0.1 else "member"
        )
        group_members.append({
            "userId": user_id,
            "groupId": g_id,
            "role": role,
            "joinedAt": groups[-1]["createdAt"]
        })

# ============================================
# GÉNÉRATION REPORTS
# ============================================
print("Génération des reports")
reports = []
report_relations = []

# Création des reports avec type
reportable_entities = (
    [{"type": "Post", "id": p["id"]} for p in posts] +
    [{"type": "Comment", "id": c["id"]} for c in comments] +
    [{"type": "User", "id": u["id"]} for u in random.sample(users, k=min(500, len(users)))]  # sample d'users
)

for i in range(N_REPORTS):
    entity = random.choice(reportable_entities)
    reporter = random.choice(all_users)

    # un user ne peut pas se reporter lui-même
    if entity["type"] == "User" and entity["id"] == reporter:
        continue
    
    report_id = f"r_{i+1:05d}"
    
    # création du report
    reports.append({
        "id": report_id,
        "reason": random.choice(REPORT_REASONS),
        "status": random.choice(REPORT_STATUS),
        "createdAt": ndt(DAYS)
    })

    # relation REPORTED et TARGET
    report_relations.append({
        "reportId": report_id,
        "reportedBy": reporter,
        "targetType": entity["type"],
        "targetId": entity["id"]
    })

# ============================================
# EXPORT
# ============================================
print("Export des fichiers...")
dump_ndjson("data/users.ndjson", users)
dump_ndjson("data/follows.ndjson", follows)
dump_ndjson("data/posts.ndjson", posts)
dump_ndjson("data/post_tags.ndjson", post_tags)
dump_ndjson("data/likes.ndjson", likes)
dump_ndjson("data/comments.ndjson", comments)
dump_ndjson("data/groups.ndjson", groups)
dump_ndjson("data/group_members.ndjson", group_members)
dump_ndjson("data/reports.ndjson", reports)
dump_ndjson("data/report_relations.ndjson", report_relations) 

print("\n✅ Génération terminée !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
print(f"  Users: {len(users)}")
print(f"  Follows: {len(follows)}")
print(f"  Posts: {len(posts)}")
print(f"  Likes: {len(likes)}")
print(f"  Comments: {len(comments)}")
print(f"  Groups: {len(groups)}")
print(f"  Group members: {len(group_members)}")
print(f"  Reports: {len(reports)}")
print(f"  Report relations: {len(report_relations)}")

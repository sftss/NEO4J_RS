import os,json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

DATA_DIR = "data"

class Neo4jImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Nettoie la base de données"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Base de données nettoyée")
    
    def create_constraints(self):
        """Crée les contraintes et index"""
        constraints = [
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT post_id IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT comment_id IF NOT EXISTS FOR (c:Comment) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT report_id IF NOT EXISTS FOR (r:Report) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT group_id IF NOT EXISTS FOR (g:Group) REQUIRE g.id IS UNIQUE",
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    pass  # Contrainte existe déjà
        print("✅ Contraintes créées")
    
    def load_ndjson(self, filename):
        """Charge un fichier NDJSON"""
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f]
    
    def import_users(self):
        """Import des utilisateurs"""
        users = self.load_ndjson("users.ndjson")
        users = [u for u in users if u.get('id')]  # Filtrer les IDs null
        
        query = """
        UNWIND $users AS user
        MERGE (u:User {id: user.id})
        SET u.username = user.username,
            u.name = user.name,
            u.privacy = user.privacy,
            u.createdAt = datetime(user.createdAt)
        """
        
        with self.driver.session() as session:
            session.run(query, users=users)
        print(f"✅ {len(users)} utilisateurs importés")

    def import_follows(self):
        """Import des relations FOLLOWS"""
        follows = self.load_ndjson("follows.ndjson")
        follows = [f for f in follows if f.get('followerId') and f.get('followedId')]
        
        query = """
        UNWIND $follows AS follow
        MATCH (follower:User {id: follow.followerId})
        MATCH (followed:User {id: follow.followedId})
        MERGE (follower)-[r:FOLLOWS]->(followed)
        SET r.since = datetime(follow.since)
        """
        
        with self.driver.session() as session:
            session.run(query, follows=follows)
        print(f"✅ {len(follows)} follows importés")

    def import_posts(self):
        """Import des posts"""
        posts = self.load_ndjson("posts.ndjson")
        posts = [p for p in posts if p.get('id') and p.get('authorId')]
        
        query = """
        UNWIND $posts AS post
        MATCH (author:User {id: post.authorId})
        MERGE (p:Post {id: post.id})
        SET p.content = post.content,
            p.mediaUrl = post.mediaUrl,
            p.visibility = post.visibility,
            p.likeCount = post.likeCount,
            p.commentCount = post.commentCount,
            p.createdAt = datetime(post.createdAt)
        MERGE (author)-[:POSTED]->(p)
        """
        
        with self.driver.session() as session:
            session.run(query, posts=posts)
        print(f"✅ {len(posts)} posts importés")

    def import_post_tags(self):
        """Import des tags"""
        post_tags = self.load_ndjson("post_tags.ndjson")
        
        # Filtrer les entrées invalides
        post_tags = [
            pt for pt in post_tags 
            if pt.get('postId') and pt.get('tagName') and pt['tagName'].strip()
        ]
        
        if not post_tags:
            print("⚠️  Aucun tag valide à importer")
            return
        
        query = """
        UNWIND $post_tags AS pt
        MATCH (p:Post {id: pt.postId})
        MERGE (t:Tag {name: pt.tagName})
        MERGE (p)-[:TAGGED_WITH]->(t)
        """
        
        with self.driver.session() as session:
            session.run(query, post_tags=post_tags)
        print(f"✅ {len(post_tags)} tags importés")

    def import_likes(self):
        """Import des likes"""
        likes = self.load_ndjson("likes.ndjson")
        likes = [l for l in likes if l.get('userId') and l.get('postId')]
        
        query = """
        UNWIND $likes AS like
        MATCH (u:User {id: like.userId})
        MATCH (p:Post {id: like.postId})
        MERGE (u)-[r:LIKED]->(p)
        SET r.likedAt = datetime(like.likedAt)
        """
        
        with self.driver.session() as session:
            session.run(query, likes=likes)
        print(f"✅ {len(likes)} likes importés")

    def import_comments(self):
        """Import des commentaires"""
        comments = self.load_ndjson("comments.ndjson")
        comments = [c for c in comments if c.get('id') and c.get('authorId') and c.get('postId')]
        
        query = """
        UNWIND $comments AS comment
        MATCH (author:User {id: comment.authorId})
        MATCH (p:Post {id: comment.postId})
        MERGE (c:Comment {id: comment.id})
        SET c.content = comment.content,
            c.createdAt = datetime(comment.createdAt)
        MERGE (author)-[:COMMENTED]->(c)
        MERGE (c)-[:ON]->(p)
        """
        
        with self.driver.session() as session:
            session.run(query, comments=comments)
        print(f"✅ {len(comments)} commentaires importés")

    def import_groups(self):
        """Import des groupes"""
        groups = self.load_ndjson("groups.ndjson")
        groups = [g for g in groups if g.get('id') and g.get('createdBy')]
        
        query = """
        UNWIND $groups AS group
        MATCH (creator:User {id: group.createdBy})
        MERGE (g:Group {id: group.id})
        SET g.name = group.name,
            g.description = group.description,
            g.visibility = group.visibility,
            g.createdAt = datetime(group.createdAt)
        MERGE (creator)-[:CREATED]->(g)
        """
        
        with self.driver.session() as session:
            session.run(query, groups=groups)
        print(f"✅ {len(groups)} groupes importés")

    def import_group_members(self):
        """Import des membres de groupes"""
        members = self.load_ndjson("group_members.ndjson")
        members = [m for m in members if m.get('userId') and m.get('groupId')]
        
        query = """
        UNWIND $members AS member
        MATCH (u:User {id: member.userId})
        MATCH (g:Group {id: member.groupId})
        MERGE (u)-[r:MEMBER_OF]->(g)
        SET r.role = member.role,
            r.joinedAt = datetime(member.joinedAt)
        """
        
        with self.driver.session() as session:
            session.run(query, members=members)
        print(f"✅ {len(members)} membres de groupes importés")

    def import_reports(self):
        """Import des reports"""
        reports = self.load_ndjson("reports.ndjson")
        reports = [r for r in reports if r.get('id')]
        
        query = """
        UNWIND $reports AS report
        MERGE (r:Report {id: report.id})
        SET r.reason = report.reason,
            r.status = report.status,
            r.createdAt = datetime(report.createdAt)
        """
        
        with self.driver.session() as session:
            session.run(query, reports=reports)
        print(f"✅ {len(reports)} reports importés")

    def import_report_relations(self):
        """Import des relations de reports"""
        relations = self.load_ndjson("report_relations.ndjson")
        relations = [
            r for r in relations 
            if r.get('reportedBy') and r.get('reportId') and r.get('targetType') and r.get('targetId')
        ]
        
        # Import en 3 passes selon le type de cible
        for target_type in ['Post', 'Comment', 'User']:
            filtered = [r for r in relations if r['targetType'] == target_type]
            
            if not filtered:
                continue
            
            if target_type == 'Post':
                query = """
                UNWIND $relations AS rel
                MATCH (u:User {id: rel.reportedBy})
                MATCH (r:Report {id: rel.reportId})
                MATCH (target:Post {id: rel.targetId})
                MERGE (u)-[:REPORTED]->(r)
                MERGE (r)-[:TARGET]->(target)
                """
            elif target_type == 'Comment':
                query = """
                UNWIND $relations AS rel
                MATCH (u:User {id: rel.reportedBy})
                MATCH (r:Report {id: rel.reportId})
                MATCH (target:Comment {id: rel.targetId})
                MERGE (u)-[:REPORTED]->(r)
                MERGE (r)-[:TARGET]->(target)
                """
            else:  # User
                query = """
                UNWIND $relations AS rel
                MATCH (u:User {id: rel.reportedBy})
                MATCH (r:Report {id: rel.reportId})
                MATCH (target:User {id: rel.targetId})
                MERGE (u)-[:REPORTED]->(r)
                MERGE (r)-[:TARGET]->(target)
                """
            
            with self.driver.session() as session:
                session.run(query, relations=filtered)
        
        print(f"✅ {len(relations)} relations de reports importées")
    
    def run_full_import(self):
        """Lance l'import complet"""
        print("🚀 Début de l'import...")
        
        self.clear_database()
        self.create_constraints()
        
        self.import_users()
        self.import_follows()
        self.import_posts()
        self.import_post_tags()
        self.import_likes()
        self.import_comments()
        self.import_groups()
        self.import_group_members()
        self.import_reports()
        self.import_report_relations()
        
        print("\n✅ Import terminé avec succès!")

if __name__ == "__main__":
    importer = Neo4jImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        importer.run_full_import()
    finally:
        importer.close()

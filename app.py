import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER", "neo4j")
PWD  = os.getenv("NEO4J_PASSWORD")
DB   = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(URI, auth=(USER, PWD))

def ping():
    with driver.session(database=DB) as session:
        return session.run("RETURN 1 AS ok").single()["ok"]

def create_user(user_id: str, username: str):
    query = """
    MERGE (u:User {id: $id})
    ON CREATE SET u.username = $username, u.createdAt = datetime()
    RETURN u
    """
    with driver.session(database=DB) as session:
        rec = session.run(query, id=user_id, username=username).single()
        return rec["u"]

def follow(follower_id: str, followee_id: str):
    query = """
    MATCH (a:User {id: $a}), (b:User {id: $b})
    MERGE (a)-[r:FOLLOWS]->(b)
    ON CREATE SET r.since = date()
    RETURN type(r) AS rel
    """
    with driver.session(database=DB) as session:
        return session.run(query, a=follower_id, b=followee_id).single()["rel"]

def user_feed(user_id: str, limit: int = 10):
    query = """
    MATCH (:User {id: $u})-[:FOLLOWS]->(f:User)-[:POSTED]->(p:Post)
    RETURN p
    ORDER BY p.createdAt DESC
    LIMIT $limit
    """
    with driver.session(database=DB) as session:
        return [r["p"] for r in session.run(query, u=user_id, limit=limit)]

if __name__ == "__main__":
    print("Ping:", ping())
    create_user("u1", "alice")
    create_user("u2", "bob")
    follow("u1", "u2")
    print("OK ✅")
    driver.close()

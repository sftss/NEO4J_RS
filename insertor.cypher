CALL apoc.periodic.iterate(
  "CALL apoc.load.json('file:///users.ndjson') YIELD value RETURN value",
  "MERGE (u:User {id:value.id})
   ON CREATE SET u.username=value.username, u.createdAt=datetime(value.createdAt), u.community=value.community",
  {batchSize:1000, parallel:true});

CALL apoc.periodic.iterate(
  "CALL apoc.load.json('file:///data/posts.ndjson') YIELD value RETURN value",
  "MERGE (p:Post {id:value.id})
   ON CREATE SET p.createdAt=datetime(value.createdAt)
   WITH p, value
   MERGE (a:User {id:value.authorId})
   MERGE (a)-[:POSTED]->(p)
   MERGE (t:Topic {id:value.topic})
   MERGE (p)-[:IN_TOPIC]->(t)",
  {batchSize:1000, parallel:true});

CALL apoc.periodic.iterate(
  "CALL apoc.load.json('file:///follows.ndjson') YIELD value RETURN value",
  "MERGE (a:User {id:value.src})
   MERGE (b:User {id:value.dst})
   MERGE (a)-[:FOLLOWS]->(b)",
  {batchSize:2000, parallel:true});

CALL apoc.periodic.iterate(
  "CALL apoc.load.json('file:///post_tags.ndjson') YIELD value RETURN value",
  "MERGE (p:Post {id:value.postId})
   MERGE (tg:Tag {name:value.tag})
   MERGE (p)-[:HAS_TAG]->(tg)",
  {batchSize:2000, parallel:true});

CALL apoc.periodic.iterate(
  "CALL apoc.load.json('file:///likes.ndjson') YIELD value RETURN value",
  "MERGE (u:User {id:value.userId})
   MERGE (p:Post {id:value.postId})
   MERGE (u)-[r:LIKED]->(p)
   ON CREATE SET r.createdAt=datetime(value.createdAt)",
  {batchSize:5000, parallel:true});

CALL apoc.periodic.iterate(
  "CALL apoc.load.json('file:///comments.ndjson') YIELD value RETURN value",
  "MERGE (c:Comment {id:value.id})
   ON CREATE SET c.text=value.text, c.createdAt=datetime(value.createdAt)
   WITH c, value
   MERGE (u:User {id:value.authorId})
   MERGE (p:Post {id:value.postId})
   MERGE (u)-[:COMMENTED]->(c)
   MERGE (c)-[:ON]->(p)",
  {batchSize:2000, parallel:true});

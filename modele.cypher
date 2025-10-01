/* Contraintes/Index */

// id
CREATE CONSTRAINT user_id IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT post_id IF NOT EXISTS
FOR (p:Post) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT comment_id IF NOT EXISTS
FOR (c:Comment) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT tag_name IF NOT EXISTS
FOR (t:Tag) REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT topic_id IF NOT EXISTS
FOR (t:Topic) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT report_id IF NOT EXISTS
FOR (r:Report) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT group_id IF NOT EXISTS
FOR (g:Group) REQUIRE g.id IS UNIQUE;

// Index
CREATE INDEX user_username IF NOT EXISTS FOR (u:User) ON (u.username);
CREATE INDEX post_visibility IF NOT EXISTS FOR (p:Post) ON (p.visibility);
CREATE INDEX group_visibility IF NOT EXISTS FOR (g:Group) ON (g.visibility);

/* ENTITÉS */

/* User(id, username, name, privacy) */
WITH {id:'u_001', username:'lea', name:'Léa Martin', privacy:'public'} AS user
MERGE (u:User {id: user.id})
SET u.username = user.username,
    u.name     = user.name,
    u.privacy  = user.privacy;

/* Post(id, authorId, content, visibility, mediaUrl?, likeCount?, commentCount?) */
WITH {id:'p_1001', authorId:'u_001', content:'Bonjour Mont-Blanc !', visibility:'public', mediaUrl:null, likeCount:0, commentCount:0} AS post
MERGE (author:User {id: post.authorId})
MERGE (p:Post {id: post.id})
SET p.content       = post.content,
    p.visibility    = post.visibility,
    p.mediaUrl      = post.mediaUrl,
    p.likeCount     = coalesce(post.likeCount, 0),
    p.commentCount  = coalesce(post.commentCount, 0)
MERGE (author)-[:POSTED]->(p);

/* Comment(id, content, likeCount?, parentPostId) + authorId (présent dans ton exemple) */
WITH {id:'c_5001', content:'Super vue !', likeCount:2, parentPostId:'p_1001', authorId:'u_002'} AS comment
MERGE (author:User {id: comment.authorId})
MERGE (p:Post {id: comment.parentPostId})
MERGE (c:Comment {id: comment.id})
SET c.content    = comment.content,
    c.likeCount  = coalesce(comment.likeCount, 0)
MERGE (author)-[:COMMENTED]->(c)
MERGE (c)-[:ON]->(p);

/* Tag(name) (minuscules) */
WITH {name:'montblanc'} AS tag
MERGE (t:Tag {name: toLower(tag.name)});

/* Topic(id, name) */
WITH {id:'t_montagne', name:'Montagne'} AS topic
MERGE (tp:Topic {id: topic.id})
SET tp.name = topic.name;

/* Report(id, reason, status) */
WITH {id:'r_9001', reason:'spam', status:'open'} AS report
MERGE (r:Report {id: report.id})
SET r.reason = report.reason,
    r.status = report.status;

/* Group(id, name, visibility) */
WITH {id:'g_001', name:'Randonneurs MB', visibility:'public'} AS grp
MERGE (g:Group {id: grp.id})
SET g.name = grp.name,
    g.visibility = grp.visibility;

/* RELATIONS */

/* (User)-[:FOLLOWS]->(User) */
WITH {src:'u_002', dst:'u_001'} AS follow
MERGE (src:User {id: follow.src})
MERGE (dst:User {id: follow.dst})
MERGE (src)-[f:FOLLOWS]->(dst);

/* (User)-[:LIKED {at}]->(Post) un like par user/post */
WITH {userId:'u_002', postId:'p_1001', at:'2025-09-21T09:15:00Z'} AS like
MERGE (u:User {id: like.userId})
MERGE (p:Post {id: like.postId})
MERGE (u)-[l:LIKED]->(p)
ON CREATE SET l.at = datetime(like.at);

/* (Post)-[:HAS_TAG]->(Tag) pls tag */
WITH {postId:'p_1001', tags:['montblanc','voyage']} AS post_tags
MERGE (p:Post {id: post_tags.postId})
WITH p, [tag IN post_tags.tags | toLower(tag)] AS tags
UNWIND tags AS tg
MERGE (t:Tag {name: tg})
MERGE (p)-[:HAS_TAG]->(t);

/* (Post)-[:IN_TOPIC]->(Topic) */
WITH {postId:'p_1001', topicId:'t_montagne'} AS post_topic
MERGE (p:Post {id: post_topic.postId})
MERGE (tp:Topic {id: post_topic.topicId})
MERGE (p)-[:IN_TOPIC]->(tp);

/* (User)-[:MEMBER_OF {role}]->(Group) */
WITH {userId:'u_001', groupId:'g_001', role:'admin'} AS membership
MERGE (u:User {id: membership.userId})
MERGE (g:Group {id: membership.groupId})
MERGE (u)-[m:MEMBER_OF]->(g)
ON CREATE SET m.role = membership.role;

/* (User)-[:REPORTED]->(Report)-[:TARGET]->(Post|Comment|User) */
WITH {reportId:'r_9001', kind:'Post', id:'p_1001'} AS tgt, 'u_003' AS reporter
MERGE (u:User {id: reporter})
MERGE (r:Report {id: tgt.reportId})
MERGE (u)-[:REPORTED]->(r)
CALL {
  WITH r, tgt
  WITH r, tgt WHERE tgt.kind = 'Post'
  MERGE (p:Post {id: tgt.id})
  MERGE (r)-[:TARGET]->(p)
  RETURN 1
}
CALL {
  WITH r, tgt
  WITH r, tgt WHERE tgt.kind = 'Comment'
  MERGE (c:Comment {id: tgt.id})
  MERGE (r)-[:TARGET]->(c)
  RETURN 1
}
CALL {
  WITH r, tgt
  WITH r, tgt WHERE tgt.kind = 'User'
  MERGE (uu:User {id: tgt.id})
  MERGE (r)-[:TARGET]->(uu)
  RETURN 1
}
RETURN 'report linked' AS status;

/* REQUÊTES tests */

/* amis suivis */
WITH 'u_002' AS userId
MATCH (me:User {id: userId})-[:FOLLOWS]->(u)-[:POSTED]->(p:Post)
WHERE p.visibility IN ['public','followers']
RETURN u.username AS author, p.id AS post, p.content AS content, p.visibility AS visibility
ORDER BY p.id DESC LIMIT 50;

/* suggestions amis d’amis */
WITH 'u_002' AS userId
MATCH (me:User {id: userId})-[:FOLLOWS]->(:User)-[:FOLLOWS]->(cand:User)
WHERE NOT exists((me)-[:FOLLOWS]->(cand)) AND me <> cand
RETURN cand.id AS candidate, count(*) AS mutual
ORDER BY mutual DESC LIMIT 10;

/* chemin d’un like */
WITH 'u_002' AS userId, 'p_1001' AS postId
MATCH (me:User {id: userId})
MATCH path = (me)-[:FOLLOWS]->(:User)-[:LIKED]->(p:Post {id: postId})
RETURN path LIMIT 5;

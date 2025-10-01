/* ============================================ */
/*  CONTRAINTES ET INDEX                        */
/* ============================================ */

// Contraintes d'unicité
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT post_id IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT comment_id IF NOT EXISTS FOR (c:Comment) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT report_id IF NOT EXISTS FOR (r:Report) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT group_id IF NOT EXISTS FOR (g:Group) REQUIRE g.id IS UNIQUE;

// Index de recherche
CREATE INDEX user_username IF NOT EXISTS FOR (u:User) ON (u.username);
CREATE INDEX post_visibility IF NOT EXISTS FOR (p:Post) ON (p.visibility);
CREATE INDEX group_visibility IF NOT EXISTS FOR (g:Group) ON (g.visibility);
CREATE INDEX user_privacy IF NOT EXISTS FOR (u:User) ON (u.privacy);

/* ============================================ */
/*  ENTITÉS                                     */
/* ============================================ */

/* User(id, username, name, privacy, createdAt) */
WITH {id:'u_001', username:'lea', name:'Léa Martin', privacy:'public',createdAt: '2024-01-15T10:30:00'} AS user
MERGE (u:User {id: user.id})
SET u.username = user.username,
    u.name     = user.name,
    u.privacy  = user.privacy,
    u.createdAt = datetime(user.createdAt);

/* Post(id, authorId, content, visibility, mediaUrl, likeCount, commentCount, createdAt) */
WITH {id:'p_1001', authorId:'u_001', content:'Je suis au Mont-Blanc', visibility:'public', mediaUrl:'https://cdn.example.com/images/abc123.jpg', likeCount:5, commentCount:2,createdAt: '2025-01-20T15:45:00'} AS post
MERGE (author:User {id: post.authorId})
MERGE (p:Post {id: post.id})
SET p.content       = post.content,
    p.visibility    = post.visibility,
    p.mediaUrl      = post.mediaUrl,
    p.likeCount     = coalesce(post.likeCount, 0),
    p.commentCount  = coalesce(post.commentCount, 0),
    p.createdAt     = datetime(post.createdAt)
MERGE (author)-[:POSTED]->(p);

/* Comment(id, content, parentPostId, authorId, createdAt) */
WITH {id:'c_5001', content:'Super vue !', parentPostId:'p_1001', authorId:'u_002',createdAt: '2025-01-21T09:12:00'} AS comment
MERGE (author:User {id: comment.authorId})
MERGE (p:Post {id: comment.parentPostId})
MERGE (c:Comment {id: comment.id})
SET c.content    = comment.content,
    c.createdAt  = datetime(comment.createdAt)
MERGE (author)-[:COMMENTED]->(c)
MERGE (c)-[:ON]->(p);

/* Tag(name) */
WITH {name:'montblanc'} AS tag
MERGE (t:Tag {name: toLower(tag.name)});

/* Topic(id, name) */
WITH {id:'t_montagne', name:'Montagne'} AS topic
MERGE (tp:Topic {id: topic.id})
SET tp.name = topic.name;

/* Report(id, reason, status, createdAt) */
WITH {id:'r_9001', reason:'spam', status:'open',createdAt: '2025-01-22T14:30:00'} AS report
MERGE (r:Report {id: report.id})
SET r.reason = report.reason,
    r.status = report.status,
    r.createdAt = datetime(report.createdAt);

/* Group(id, name, visibility, createdAt) */
WITH {id:'g_001', name:'Randonneurs MB', visibility:'public',createdAt: '2024-06-10T10:00:00'} AS grp
MERGE (g:Group {id: grp.id})
SET g.name = grp.name,
    g.visibility = grp.visibility,
    g.createdAt = datetime(grp.createdAt);

/* ============================================ */
/*  RELATIONS                                   */
/* ============================================ */

/* (User)-[:FOLLOWS {since}]->(User) */
WITH {src:'u_002', dst:'u_001', since: '2025-01-10T12:00:00'} AS follow
MERGE (src:User {id: follow.src})
MERGE (dst:User {id: follow.dst})
MERGE (src)-[f:FOLLOWS]->(dst)
ON CREATE SET f.since = datetime(follow.since);

/* (User)-[:LIKED {createdAt}]->(Post) */
WITH {userId:'u_002', postId:'p_1001', createdAt:'2025-09-21T09:15:00'} AS like
MERGE (u:User {id: like.userId})
MERGE (p:Post {id: like.postId})
MERGE (u)-[l:LIKED]->(p)
ON CREATE SET l.createdAt = datetime(like.createdAt);

/* (Post)-[:HAS_TAG]->(Tag) */
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

/* (User)-[:MEMBER_OF {role, joinedAt}]->(Group) */
WITH {userId:'u_001', groupId:'g_001', role:'admin',joinedAt: '2024-06-10T10:05:00'} AS membership
MERGE (u:User {id: membership.userId})
MERGE (g:Group {id: membership.groupId})
MERGE (u)-[m:MEMBER_OF]->(g)
ON CREATE SET m.role = membership.role,
              m.joinedAt = datetime(membership.joinedAt);

/* (User)-[:REPORTED]->(Report)-[:TARGET]->(Post|Comment|User) - Version simplifiée */
WITH {
    reportId:'r_9001', 
    reportedBy: 'u_003',
    targetType: 'Post',  // 'Post', 'Comment', ou 'User'
    targetId: 'p_1001'
} AS rep
MERGE (u:User {id: rep.reportedBy})
MERGE (r:Report {id: rep.reportId})
MERGE (u)-[:REPORTED]->(r)

FOREACH (ignoreMe IN CASE WHEN rep.targetType = 'Post' THEN [1] ELSE [] END |
  MERGE (p:Post {id: rep.targetId})
  MERGE (r)-[:TARGET]->(p)
)
FOREACH (ignoreMe IN CASE WHEN rep.targetType = 'Comment' THEN [1] ELSE [] END |
  MERGE (c:Comment {id: rep.targetId})
  MERGE (r)-[:TARGET]->(c)
)
FOREACH (ignoreMe IN CASE WHEN rep.targetType = 'User' THEN [1] ELSE [] END |
  MERGE (uu:User {id: rep.targetId})
  MERGE (r)-[:TARGET]->(uu)
);

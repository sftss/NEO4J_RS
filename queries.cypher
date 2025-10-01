// Explorer 50 nœuds aléatoires et leurs relations
MATCH (n)
WITH n, rand() AS random
ORDER BY random
LIMIT 10

MATCH (n)-[r]-(m)
RETURN n, r, m
LIMIT 150

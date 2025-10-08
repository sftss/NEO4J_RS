// Ne marche plus tant que l'extension Neo4j ne revient pas
MATCH (n)
WITH n, rand() AS random
ORDER BY random
LIMIT 10

MATCH (n)-[r]-(m)
RETURN n, r, m
LIMIT 150

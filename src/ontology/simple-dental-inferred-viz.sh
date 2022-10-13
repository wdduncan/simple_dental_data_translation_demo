runoak -i simple-dental-ontology-inferred.owl viz \
  http://simple-dental-ontology.owl/tooth_1 \
  -p i \
  -S tooth-inferred-style.json \
  --max-hops 2 \
  -o simple-tooth-inferred.png

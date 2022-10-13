runoak -i simple-dental-ontology.owl viz \
  http://simple-dental-ontology.owl/tooth_1 \
  -p i,e \
  -S style.json \
  --max-hops 2 \
  -o simple-tooth.png
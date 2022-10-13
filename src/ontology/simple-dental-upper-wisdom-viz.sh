runoak -i simple-dental-ontology.owl viz \
  http://simple-dental-ontology.owl/tooth_1 \
  http://simple-dental-ontology.owl/tooth_16 \
   http://simple-dental-ontology.owl/molar \
  -p i \
  -S style.json \
  --max-hops 3 \
  -o simple-upper-wisdom.png
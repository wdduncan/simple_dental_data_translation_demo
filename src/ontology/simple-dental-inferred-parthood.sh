runoak -i simple-dental-ontology-inferred.owl viz \
  http://simple-dental-ontology.owl/tooth_1 \
   -p i,http://simple-dental-ontology.owl/part_of \
   -S style.json \
   --max-hops 2 \
   -o simple-tooth-inferred-parthood.png

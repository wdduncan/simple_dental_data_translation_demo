runoak -i simple-dental-ontology-inferred.owl viz \
  http://simple-dental-ontology.owl/tooth \
  http://simple-dental-ontology.owl/tooth_surface \
  http://simple-dental-ontology.owl/restoration_procedure \
  http://simple-dental-ontology.owl/resin \
  http://simple-dental-ontology.owl/service_code \
   -p i,http://simple-dental-ontology.owl/part_of,http://simple-dental-ontology.owl/has_participant,http://simple-dental-ontology.owl/is_about \
   -S style.json \
   --max-hops 1 \
   -o simple-tooth-inferred-graph.png

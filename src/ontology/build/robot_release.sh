# remove any existing owl files in the directory
rm *.owl

# copy dev ontology and imports into directory
cp ../data_entity_dev.owl .
cp ../imports/*import.owl .

# since the robot.jar file is in the directory, calls to robot are made using the java -jar ./robot.jar command
# alternatively, you can call robot directly if your system is configured properly 
# for example, if the path to robot is in your PATH environment variable 
# you can perform merge by simple executing robot merge

# merge owl files
java -jar ./robot.jar merge \
  --inputs "*.owl" \
  --include-annotations true \
  --collapse-import-closure true \
  --output data_entity_merged.owl
   
# # add date to IRI version; e.g.: http://purl.obolibrary.org/obo/2018-06-05/data-source-ontology.owl
java -jar ./robot.jar annotate \
  --input data_entity_merged.owl \
  --ontology-iri "http://data_entity_ontology/data_entity.owl" \
  --version-iri "http://data_entity_ontology/`date '+%Y-%m-%d'`/data_entity.owl" \
  --output data_entity_annotated.owl

# run reasoner on the ontology and add inferred axioms to final output
java -jar ./robot.jar reason \
	--input data_entity_annotated.owl \
  --reasoner HermiT \
  --annotate-inferred-axioms true \
  --output data_entity.owl

# clean up
# remove imports
rm *import.owl

# remove dev, merge, annotated temp ontologies
# comment out these lines if you wish to examine them
rm data_entity_dev.owl
rm data_entity_merged.owl
rm data_entity_annotated.owl

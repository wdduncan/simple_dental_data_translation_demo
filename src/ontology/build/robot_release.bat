
REM remove any existing owl files in the directory
del *.owl

REM copy dev ontology and imports into directory
copy ..\data_entity_dev.owl .
copy ..\imports\*import* .

REM since the robot.jar file is in the directory, calls to robot are made using the java -jar ./robot.jar command
REM alternatively, you can call robot directly if your system is configured properly 
REM for example, if the path to robot is in your PATH environment variable 
REM you can perform merge by simple executing robot merge

REM merge owl files
"%JAVA_HOME%\bin\java.exe" -jar .\robot.jar merge^
  --inputs "*.owl"^
  --include-annotations true^
  --collapse-import-closure true^
  --output data_entity_merged.owl
   
REM add date to IRI version; e.g.: http://purl.obolibrary.org/obo/2018-06-05/data-source-ontology.owl
"%JAVA_HOME%\bin\java.exe" -jar .\robot.jar annotate^
  --input data_entity_merged.owl^
  --ontology-iri "http://data_entity_ontology/data_entity.owl"^
  --version-iri "http://data_entity_ontology/%date:~-4,4%%date:~-7,2%%date:~-10,2%/data_entity.owl"^
  --output data_entity_annotated.owl

REM run reasoner on the ontology and add inferred axioms to final output
"%JAVA_HOME%\bin\java.exe" -jar .\robot.jar reason^
	--input data_entity_annotated.owl^
  --reasoner HermiT^
  --annotate-inferred-axioms true^
  --output data_entity.owl

REM clean up
REM remove imports
del *import*

REM remove dev, merge, annotated temp ontologies
REM comment out these lines if you wish to examine them
del data_entity_dev.owl
del data_entity_merged.owl
del data_entity_annotated.owl

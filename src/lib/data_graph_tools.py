from rdflib import Graph, ConjunctiveGraph, URIRef, RDF, OWL, RDFS, Literal


def make_data_framework(df, data_type_dict):
    def add_entity(entity, owl_type):
        graph.add( (URIRef(entity["iri"]), RDF.type, URIRef(owl_type)) )

        if owl_type == OWL.Class:
            graph.add( (URIRef(entity["iri"]), RDFS.subClassOf, URIRef(entity["type"])) )
        elif owl_type == OWL.ObjectProperty or owl_type == OWL.DatatypeProperty:
            graph.add((URIRef(entity["iri"]), RDFS.subPropertyOf, URIRef(entity["type"])) )
        else:
            graph.add( (URIRef(entity["iri"]), RDF.type, URIRef(entity["type"])) )

        rdfs_label = entity["rdfs:label"] if "rdfs:label" in entity.keys() else None
        if rdfs_label:
            graph.add( (URIRef(entity["iri"]), RDFS.label, Literal(rdfs_label)) )

    def add_entities(entities, owl_type):
        for key in entities.keys():
            add_entity(entities[key], owl_type)

    graph = ConjunctiveGraph()

    ## add table class to ontology
    add_entity(data_type_dict["cls"]["table"], OWL.Class)

    ## add table individual to ontology
    add_entity(data_type_dict["i"]["table"], OWL.NamedIndividual)

    ## add table row class to ontology
    if "row" in data_type_dict["cls"].keys():
        add_entity(data_type_dict["cls"]["row"], OWL.Class)

    ## add top level field class, object property, and data property
    ## field class
    if "field" in data_type_dict["cls"].keys():
        cls = data_type_dict["cls"]["field"]
        add_entity(cls, OWL.Class)
        add_entities(cls["subtype"], OWL.Class)

    ## add cols/fields as obect properties
    if "op" in data_type_dict.keys():
        op = data_type_dict["op"]
        add_entity(op, OWL.ObjectProperty)
        add_entities(op["subtype"], OWL.ObjectProperty)

    ## add cols/fields as data properties
    if "dp" in data_type_dict.keys():
        dp = data_type_dict["dp"]
        add_entity(dp,  OWL.DatatypeProperty)
        add_entities(dp["subtype"], OWL.DatatypeProperty)

    # print(graph.serialize(format='turtle').decode("utf-8"))
    return graph


def make_data_graph(df, context, jsonld_column_name="jsonld"):
    graph = ConjunctiveGraph()
    for json_field in df[jsonld_column_name]:
        # data = json.loads(json_field)
        doc = f"""
        {{ 
            {context}, 
            "@graph": [{json_field}]
        }}
        """
        # print(doc)
        graph.parse(data=doc, format="json-ld")
    return graph

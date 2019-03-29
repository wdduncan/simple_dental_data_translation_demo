from rdflib import Graph, ConjunctiveGraph, URIRef, RDF, OWL, RDFS, Literal
import json
import pandas as pds
from requests.utils import requote_uri
from textwrap import dedent

def explode_surfaces(df_services):
    temp1 = pds.DataFrame(df_services.surfaces.apply(list).to_list())
    temp2 = temp1.stack()
    temp3 = temp2.reset_index(1).drop(['level_1'], axis=1)
    temp3.columns = ["surface"]
    df = df_services.merge(temp3, how='right', left_index=True, right_index=True)
    return df


def jsonify_haxis(series, id=None, id_key="id", type=None, type_key="type", haxis="row", vaxis="data"):
    temp = series.astype(str).to_dict() # convert row to string dict
    data = \
        {key:{"value":value} for key, value in temp.items()}

    json_data = {f"{haxis}": {f"{vaxis}": data}}
    if id and len(id_key) > 0: json_data.update({f"{id_key}": f"{id}"}) # update haxis id
    if type and len(type_key) > 0: json_data.update({f"{type_key}": f"{type}"}) # update haxis type

    return json.dumps(json_data) # return data as json


def jsonldify_row(row, data_type_dict, value_property="value", member_property="member_of",
                  record_base_iri="", field_base_iri=""):
    def row_values_dict(row_dict, field_dict):
        """
        Use list comprhension to build a dictionary of key:value pairs of items
        that are NOT in the field_dict dictionary
        :returns a dictionary with form {"key1": "value1", "key2": "value2", ...}
        """
        temp = \
            {
                key: value
                for key, value in row_dict.items() # iterate over key:value pairs in dictionary
                if key not in field_dict.keys() # only include fields NOT in the field_dict
            }
        return temp

    def row_fields_dict(row_dict, field_dict):
        """
        Use list comprhension to build a dictionary of key:value pairs of items
        that are in the field_dict dictionary
        :returns a dictionary with form {"key1": {"@type": "field_iri", "value": "value1"}, ...}
        """
        temp ={}
        for key, value in row_dict.items():  # iterate over key:value pairs in dictionary
            if key in field_dict.keys():  # only include fields in the field_dict
                temp[key] = \
                    {
                        "@type": field_dict[key]["iri"],
                        value_property: value,
                        member_property: table_iri
                    }

                ## if given, add info about individual field iri
                if len(field_base_iri) > 0:
                    field_label = f"""i:{table_name}_record_{str(row.name)}_{requote_uri(key)}"""
                    field_iri = f"""{field_base_iri}{field_label}"""
                    temp[key].update({"@id": field_iri, "label": field_label})
        return temp

    table_iri = data_type_dict["table"]["individual"]["iri"]
    table_name = data_type_dict["table"]["individual"]["name"]
    field_dict = data_type_dict["field"]["class"]

    ## initialize data with record information
    ## if given, add info about individual record iri
    record = {"@type": data_type_dict["table"]["record"]["class"]["iri"], member_property: table_iri}
    if len(record_base_iri) > 0:
        record_label = f"""i:{table_name}_record_{str(row.name)}"""
        record_iri = f"""{record_base_iri}{record_label}"""
        record.update({"@id": record_iri, "label": record_label})

    row_dict = row.astype(str).to_dict() # convert row to string dict

    value_data = row_values_dict(row_dict, field_dict) # get data as key:value pairs
    field_data = row_fields_dict(row_dict, field_dict) # get data in form key:{"@type": field_iri, "value": value}

    data = {**record, **value_data, **field_data} # merge dictionaries
    return json.dumps(data)


def append_json_column(df, json_column_name="json"):
    df[json_column_name] =  df.apply(lambda row: jsonify_haxis(row), axis=1)
    # df[json_column_name] =  df.apply(lambda row: jsonify_row(row, str(row.name)), axis=1)
    return df


def append_jsonld_column(df, data_type_dict, value_property="value", jsonld_column_name="jsonld"):
    rb_iri = data_type_dict["table"]["record"]["individual"]["base_iri"]
    fb_iri = data_type_dict["table"]["field"]["individual"]["base_iri"]
    df[jsonld_column_name] = \
        df.apply(lambda row:
                 jsonldify_row(
                    row,
                    data_type_dict,
                    value_property,
                    record_base_iri=rb_iri,
                    field_base_iri=fb_iri),
                 axis=1)
    return df


def make_data_framework(df, data_type_dict):
    def add_entity(graph, entity, owl_type):
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

    def add_entities(graph, entities, owl_type):
        for key in entities.keys():
            add_entity(graph, entities[key], owl_type)

    graph = ConjunctiveGraph()

    ## add table class to ontology
    add_entity(graph, data_type_dict["cls"]["table"], OWL.Class)

    ## add table individual to ontology
    add_entity(graph, data_type_dict["i"]["table"], OWL.NamedIndividual)

    ## add table row class to ontology
    if "row" in data_type_dict["cls"].keys():
        add_entity(graph, data_type_dict["cls"]["row"], OWL.Class)

    ## add top level field class, object property, and data property
    ## field class
    if "field" in data_type_dict["cls"].keys():
        cls = data_type_dict["cls"]["field"]
        add_entity(graph, cls, OWL.Class)

    ## add cols/fields as obect properties
    if "op" in data_type_dict.keys():
        op = data_type_dict["op"]
        add_entity(graph, op, OWL.ObjectProperty)
        add_entities(graph, op["subtype"], OWL.ObjectProperty)

    ## add cols/fields as data properties
    if "dp" in data_type_dict.keys():
        dp = data_type_dict["dp"]
        add_entity(graph, dp,  OWL.DatatypeProperty)
        add_entities(graph, dp["subtype"], OWL.DatatypeProperty)

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
        # print(data['patient_id'])
        graph.parse(data=doc, format='json-ld')
    return graph


def translate_data(df, data_type_dict, context, print_graph=False):

    df = append_json_column(df)
    # print(str(df.json))
    # print(str(df))

    # df = append_jsonld_column(df, data_type_dict)
    # print(str(df.jsonld))

    framework_graph = make_data_framework(df, data_type_dict)
    print(framework_graph.serialize(format='turtle').decode("utf-8"))
    # data_graph = make_data_graph(df, context)
    # graph = framework_graph + data_graph
    # if print_graph: print(graph.serialize(format='turtle').decode("utf-8"))
    # return graph
    return df

if __name__ == "__main__":
    deo_graph = Graph().parse("ontology/data_entity.owl")
    dental_graph = Graph().parse("ontology/simple-dental-ontology.owl")

    # pds.set_option("display.width", 1000)
    pds.set_option('display.max_colwidth', 200)

    df_patients1 = pds.read_excel("data/patients_1.xlsx")
    with open("data/patients_1_dict.v2.txt", "r") as dict_file:
        patients_1_type_dict = eval(dict_file.read())

    with open("data/patients_1_context.v2.txt", "r") as context_file:
        patients_1_context = context_file.read()

    translate_data(df_patients1, patients_1_type_dict, patients_1_context)

    # patients_1_graph = translate_data(df_patients1, patients_1_type_dict, patients_1_context)
    # graph = deo_graph + patients_1_graph
    # graph.serialize(destination="output/patients_1.ttl", format="turtle")
    #
    # df_patients2 = pds.read_excel("data/patients_2.xlsx")
    # with open("data/patients_2_dict.txt", "r") as dict_file:
    #     patients_2_type_dict = eval(dict_file.read())
    #
    # with open("data/patients_2_context.txt", "r") as context_file:
    #     patients_2_context = context_file.read()
    #
    # patients_2_graph = translate_data(df_patients2, patients_2_type_dict, patients_2_context)
    # graph = deo_graph + patients_2_graph
    # graph.serialize(destination="output/patients_2.ttl", format="turtle")
    #
    # patients_graph = deo_graph + patients_1_graph + patients_2_graph
    # patients_graph.serialize(destination="output/patients.ttl", format="turtle")
    #
    # df_services1 = explode_surfaces(pds.read_excel("data/services_1.xlsx"))
    # with open("data/services_1_dict.txt", "r") as dict_file:
    #     services_1_type_dict = eval(dict_file.read())
    #
    # with open("data/services_1_context.txt", "r") as context_file:
    #     services_1_context = context_file.read()
    #
    # services_1_graph = translate_data(df_services1, services_1_type_dict, services_1_context)
    # graph = deo_graph + services_1_graph
    # graph.serialize(destination="output/services_1.ttl", format="turtle")
    #
    # df_services2 = explode_surfaces(pds.read_excel("data/services_2.xlsx"))
    # with open("data/services_2_dict.txt", "r") as dict_file:
    #     services_2_type_dict = eval(dict_file.read())
    #
    # with open("data/services_2_context.txt", "r") as context_file:
    #     services_2_context = context_file.read()
    #
    # services_2_graph = translate_data(df_services2, services_2_type_dict, services_2_context)
    # graph = deo_graph + services_2_graph
    # graph.serialize(destination="output/services_2.ttl", format="turtle")
    #
    # services_graph = deo_graph + services_1_graph + services_2_graph
    # services_graph.serialize(destination="output/services.ttl", format="turtle")
    #
    # data_data_graph = deo_graph + patients_graph + services_graph + dental_graph
    # data_data_graph.serialize(destination="output/dental_data.ttl", format="turtle")
    #
    # # print(deo_graph.serialize().decode("utf-8"))

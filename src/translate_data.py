from rdflib import Graph, ConjunctiveGraph, URIRef, RDF, OWL, RDFS, Literal
import pandas as pds
from src.lib import json_tools as jt
import json
# from requests.utils import requote_uri
from urllib.parse import quote
# from textwrap import dedent

def explode_surfaces(df_services):
    temp1 = pds.DataFrame(df_services.surfaces.apply(list).to_list())
    temp2 = temp1.stack()
    temp3 = temp2.reset_index(1).drop(['level_1'], axis=1)
    temp3.columns = ["surface"]
    df = df_services.merge(temp3, how='right', left_index=True, right_index=True)
    return df


def append_json_column(df, json_column_name="json"):
    df[json_column_name] =  df.apply(lambda row: jt.jsonify_series(row), axis=1)
    # df[json_column_name] =  df.apply(lambda row: jsonify_row(row, str(row.name)), axis=1)
    return df


def append_jsonld_column(df, data_type_dict, jsonld_column_name="jsonld", json_column_name="json", haxis="row"):
    # create json data with table iri and relate to data using "has_row" key
    row_type = data_type_dict["i"]["row"]["type"]
    df[jsonld_column_name] = \
        df[json_column_name].map(lambda row: jt.jsonldify_values(row, data_type_dict, _type=row_type))

    # add id & label info to each "has_row" data block
    for idx, json_data in df[[jsonld_column_name]].itertuples():
        row_id = data_type_dict["i"]["row"]["ns"] + "row_" + str(idx) # build id
        json_data = jt.json_update(json_data, update_key="_id", update_value=row_id, data_key="has_row")

        row_label = data_type_dict["i"]["table"]["table_name"] + ".row_" + str(idx) # build label
        json_data = jt.json_update(json_data, update_key="_label", update_value=row_label, data_key="has_row")

        df.at[idx, jsonld_column_name] = json_data # update data frame

    return df


def append_jsonld_column2(df, data_type_dict, jsonld_column_name="jsonld", json_column_name="json", haxis="row"):
    def update_data(data, udate_key, update_value):
        ## if data is in a list; update each item;
        ## json_update returns a string (i.e., json) so use loads to convert to a dict
        if type([]) == type(data):
            new_data = \
                list(map(lambda d: json.loads(jt.json_update(d, udate_key, update_value)), data))
        else:
            new_data = \
                json.loads(jt.json_update(data, udate_key, update_value))
        return new_data

    # create json data with table iri and relate to data using "has_row" key
    row_type = data_type_dict["i"]["row"]["type"]
    df[jsonld_column_name] = \
        df[json_column_name].map(lambda row: jt.jsonldify_values(row, data_type_dict, _type=row_type))

    # add id & label info to each "has_row" data block
    for idx, json_data in df[[jsonld_column_name]].itertuples():
        row_id = data_type_dict["i"]["row"]["ns"] + "row_" + str(idx) # build id
        json_data = jt.json_update(json_data, update_key="_id", update_value=row_id, data_key="has_row")

        row_label = data_type_dict["i"]["table"]["table_name"] + ".row_" + str(idx) # build label
        json_data = jt.json_update(json_data, update_key="_label", update_value=row_label, data_key="has_row")

        df.at[idx, jsonld_column_name] = json_data # update data frame


    fields = data_type_dict["i"]["field"]["subtype"]
    for idx, json_data in df[[jsonld_column_name]].itertuples():
        jdata = jt.json_as_dict(json_data)
        for field in fields:
            # print(field)

            field_data = jdata["has_row"][field]
            field_type = fields[field]["type"]
            # field_data = convert_data(field_data)
            # field_data = update_data(field_data, "_type", fields[field]["type"])
            field_data = update_data(field_data, "_type", field_type)

            field_id = data_type_dict["i"]["field"]["ns"] + "row_" + str(idx) + "." + quote(field)  # build id
            # field_data = json_update(field_data, update_key="_id", update_value=field_id)
            field_data = update_data(field_data, "_id", field_id)

            field_label = data_type_dict["i"]["table"]["table_name"] + ".row_" + str(idx) + "." + field  # build label
            # field_data = json_update(field_data, update_key="_label", update_value=field_label)
            field_data = update_data(field_data, "_label", field_label)

            # print(field_data)
            # print(jdata["has_row"][field])
            jdata["has_row"][field] = field_data
            # print(jdata["has_row"][field])
            # print(jdata)
            df.at[idx, jsonld_column_name] = json.dumps(jdata)

    return df


def append_jsonld_column3(df, data_type_dict, jsonld_column_name="jsonld", json_column_name="json", field_inst=False):
    def update_data(data, udate_key, update_value):
        ## if data is in a list; update each item;
        ## json_update returns a string (i.e., json) so use loads to convert to a dict
        if type([]) == type(data):
            new_data = \
                list(map(lambda d: json.loads(jt.json_update(d, udate_key, update_value)), data))
        else:
            new_data = \
                json.loads(jt.json_update(data, udate_key, update_value))
        return new_data

    ## transform the json data in each row into json-ld that specifies the table that the
    ## row is a member of and gives the row id and label
    df[jsonld_column_name] = \
        df.apply(lambda row: jt.jsonldify_row(row, json_column_name, data_type_dict), axis=1)

    ## tranform json data values into instances of data fields
    if field_inst:
        df[jsonld_column_name] = jt.jsonldify_fields(df, jsonld_column_name, data_type_dict)

    return df


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


def translate_data(df, data_type_dict, context, print_graph=False):

    df = append_json_column(df)

    # df = append_jsonld_column(df, data_type_dict)
    # df = append_jsonld_column2(df, data_type_dict) # **********
    df = append_jsonld_column3(df, data_type_dict, field_inst=True) # **********
    # print(str(df.jsonld))

    framework_graph = make_data_framework(df, data_type_dict)
    data_graph = make_data_graph(df, context)
    graph = framework_graph + data_graph
    if print_graph: print(graph.serialize(format='turtle').decode("utf-8"))
    return graph

if __name__ == "__main__":
    deo_graph = Graph().parse("ontology/data_entity.owl")
    dental_graph = Graph().parse("ontology/simple-dental-ontology.owl")

    # pds.set_option("display.width", 1000)
    pds.set_option('display.max_colwidth', 200)

    df_patients1 = pds.read_excel("data/patients_1.xlsx")
    with open("data/patients_1_dict.v2.txt", "r") as dict_file:
        patients_1_type_dict = eval(dict_file.read())

    ## append surfaces column for testing
    df_patients1["tooth_surface"] = "mod"
    df_patients1["tooth_surface"] = df_patients1["tooth_surface"].map(list)
    # print(df_patients1)

    with open("data/patients_1_context.v3.txt", "r") as context_file: # **********
        patients_1_context = context_file.read()

    patients_1_graph = translate_data(df_patients1, patients_1_type_dict, patients_1_context)
    graph = deo_graph + patients_1_graph
    graph.serialize(destination="output/patients_1.ttl", format="turtle")
    # print(graph.serialize(format='turtle').decode("utf-8"))
    print(patients_1_graph.serialize(format='turtle').decode("utf-8"))

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

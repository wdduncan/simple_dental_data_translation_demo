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


def jsonify_series(series):
    def convert(value):
        if type([]) == type(value) or type(()) == type(value):
            new_value = list(map(lambda v: {"_value": str(v)}, value))
        else:
            new_value = {"_value": str(value)}
        return new_value

    ## for each item in series dictionary items, convert the item value into the form {"_value": value}
    ## note: the convert function is needed for cases in which value is a list
    data = {key: convert(value) for key, value in series.to_dict().items()}
    return json.dumps(data) # return data as json


def jsonldify_values(json_data, data_type_dict, _id=None, _id_key="_id",
                      _type="data_row", _type_key="_type", data_key="has_row"):
    ## load data into dict; add type and id info
    ## note: json_update returns a json object, so it has be converted to a dict
    jdata = json_as_dict(json_update(json_data, _type_key, _type))
    if _id: jdata[f"{_id_key}"]: f"{id}" # add id info if given

    ## create table iri that data is a member of and relate (using data_key)
    ## the data to the table
    data = \
    {
        f"{_id_key}": data_type_dict["i"]["table"]["iri"], # add table instance iri
        f"{data_key}": jdata
    }
    return json.dumps(data) # return data as json


def json_as_dict(json_data, data_key=None):
    if data_key:
        return json.loads(json_data)[data_key]
    else:
        return json.loads(json_data)


def json_update(json_data, update_key, update_value, data_key=None):
    jdata = json_as_dict(json_data)  # load json data into dict
    if data_key:
        jdata[data_key].update({f"{update_key}": f"{update_value}"})
    else:
        jdata.update({f"{update_key}": f"{update_value}"})  # add key:value info
    return json.dumps(jdata)


def jsonldify_haxis_id(json_data, _id, _id_key="_id", data_key="has_row"):
    jdata = json_update(json_data, _id_key, _id, data_key)
    return json.dumps(jdata)  # return data as json


def jsonldify_haxis_label(json_data, _label, _label_key="_label", data_key="has_row"):
    jdata = json_update(json_data, _label_key, _label, data_key)
    return json.dumps(jdata)  # return data as json


def jsonldify_field_id(json_data, _id, _id_key="_id"):
    pass


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
    df[json_column_name] =  df.apply(lambda row: jsonify_series(row), axis=1)
    # df[json_column_name] =  df.apply(lambda row: jsonify_row(row, str(row.name)), axis=1)
    return df


def append_jsonld_column(df, data_type_dict, jsonld_column_name="jsonld", json_column_name="json", haxis="row"):
    def convert_data(data):
        if type([]) == type(data):
            new_data = list(map(lambda d: json_update(json.dumps(d), "_type", field_type), data))
        else:
            new_data = json_update(json.dumps(data), "_type", field_type)
        return new_data

    # create json data with table iri and relate to data using "has_row" key
    df[jsonld_column_name] = \
        df[json_column_name].map(lambda row: jsonldify_values(row, data_type_dict))

    # add id & label info to each "has_row" data block
    for idx, json_data in df[[jsonld_column_name]].itertuples():
        row_id = data_type_dict["i"]["row"]["ns"] + "row_" + str(idx) # build id
        json_data = json_update(json_data, update_key="_id", update_value=row_id, data_key="has_row")

        row_label = data_type_dict["i"]["table"]["table_name"] + ".row_" + str(idx) # build label
        json_data = json_update(json_data, update_key="_label", update_value=row_label, data_key="has_row")

        df.at[idx, jsonld_column_name] = json_data # update data frame


    fields = data_type_dict["i"]["field"]["subtype"]
    for idx, json_data in df[[jsonld_column_name]].itertuples():
        jdata = json_as_dict(json_data)
        for field in fields:
            # print(field)
            field_data = jdata["has_row"][field]
            field_type = fields[field]["type"]
            field_data = convert_data(field_data)

            # print(field_data)
            jdata["has_row"][field] = field_data
        # print(jdata)
        df.at[idx, jsonld_column_name] = json_data  # update data frame

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
    df = append_jsonld_column(df, data_type_dict)
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

    with open("data/patients_1_context.v2.txt", "r") as context_file:
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

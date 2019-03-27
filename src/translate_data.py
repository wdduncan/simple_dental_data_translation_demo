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


def jsonify_row(row, row_id=None, row_type=None):
    temp = row.astype(str).to_dict() # convert row to string dict
    fields = \
        {key:{"value":value} for key, value in temp.items()}

    json_row = {"row": {"field": fields}}
    if row_id: json_row.update({"id": f"{row_id}"}) # update row id
    if row_type: json_row.update({"type": f"{row_type}"}) # update row type

    return json.dumps(json_row) # return json of the row


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
    df[json_column_name] =  df.apply(lambda row: jsonify_row(row), axis=1)
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
    graph = ConjunctiveGraph()

    # get subdictionaries from dict
    table_idv = data_type_dict["table"]["individual"]
    table_class = data_type_dict["table"]["class"]
    table_record_class = data_type_dict["table"]["record"]["class"]
    table_field_class = data_type_dict["table"]["field"]["class"]
    table_field_op = data_type_dict["table"]["field"]["object_property"]
    table_field_dp = data_type_dict["table"]["field"]["data_property"]

    ## add table class to ontology
    graph.add( (URIRef(table_class["iri"]), RDF.type, OWL.Class) )
    graph.add( (URIRef(table_class["iri"]), RDFS.subClassOf, URIRef(table_class["subclass_of"])) )
    graph.add( (URIRef(table_class["iri"]), RDFS.label, Literal(table_class["rdfs:label"])) )

    ## add table individual to ontology
    graph.add( (URIRef(table_idv["iri"]), RDF.type, OWL.NamedIndividual) )
    graph.add( (URIRef(table_idv["iri"]), RDF.type, URIRef(table_idv["type"])) )
    graph.add( (URIRef(table_idv["iri"]), RDFS.label, Literal(table_idv["rdfs:label"])) )

    ## add table record class to ontology
    graph.add( (URIRef(table_record_class["iri"]), RDF.type, OWL.Class))
    graph.add( (URIRef(table_record_class["iri"]), RDFS.subClassOf, URIRef(table_record_class["subclass_of"])) )
    graph.add( (URIRef(table_record_class["iri"]), RDFS.label, Literal(table_record_class["rdfs:label"])) )

    ## add top level field class, object property, and data property
    ## field class
    graph.add( (URIRef(table_field_class["iri"]), RDF.type, OWL.Class) )
    graph.add( (URIRef(table_field_class["iri"]), RDFS.subClassOf, URIRef(table_field_class["subclass_of"])) )
    graph.add( (URIRef(table_field_class["iri"]), RDFS.label, Literal(table_field_class["rdfs:label"])) )

    ## field obect property
    graph.add( (URIRef(table_field_op["iri"]), RDF.type, OWL.ObjectProperty) )
    graph.add( (URIRef(table_field_op["iri"]), RDFS.subPropertyOf, URIRef(table_field_op["subproperty_of"])) )
    graph.add( (URIRef(table_field_op["iri"]), RDFS.label, Literal(table_field_op["rdfs:label"])) )

    ## field data property
    graph.add( (URIRef(table_field_dp["iri"]), RDF.type, OWL.DatatypeProperty) )
    graph.add( (URIRef(table_field_dp["iri"]), RDFS.subPropertyOf, URIRef(table_field_dp["subproperty_of"])) )
    graph.add( (URIRef(table_field_dp["iri"]), RDFS.label, Literal(table_field_dp["rdfs:label"])) )

    ## add columns as field classes to ontology
    field_class = data_type_dict["field"]["class"]
    for col in df.columns:
        if col in field_class.keys():
            field_iri = URIRef(field_class[col]["iri"])
            graph.add( (field_iri, RDF.type, OWL.Class) )
            graph.add( (field_iri, RDFS.subClassOf, URIRef(field_class[col]["subclass_of"])) )
            graph.add( (field_iri, RDFS.label, Literal(field_class[col]["rdfs:label"])) )

    ## add columns as field object properties to ontology
    field_op = data_type_dict["field"]["object_property"]
    for col in df.columns:
        if col in field_op.keys():
            field_iri = URIRef(field_op[col]["iri"])
            graph.add( (field_iri, RDF.type, OWL.ObjectProperty) )
            graph.add( (field_iri, RDFS.subPropertyOf, URIRef(field_op[col]["subproperty_of"])) )
            graph.add( (field_iri, RDFS.label, Literal(field_op[col]["rdfs:label"])) )

    ## add columns as field object properties to ontology
    field_dp = data_type_dict["field"]["data_property"]
    for col in df.columns:
        if col in field_dp.keys():
            field_iri = URIRef(field_dp[col]["iri"])
            graph.add( (field_iri, RDF.type, OWL.DatatypeProperty) )
            graph.add( (field_iri, RDFS.subPropertyOf, URIRef(field_dp[col]["subproperty_of"])) )
            graph.add( (field_iri, RDFS.label, Literal(field_dp[col]["rdfs:label"])) )

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
    print(str(df.json))
    # print(str(df))

    # df = append_jsonld_column(df, data_type_dict)
    # print(str(df.jsonld))

    # framework_graph = make_data_framework(df, data_type_dict)
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
    with open("data/patients_1_dict.txt", "r") as dict_file:
        patients_1_type_dict = eval(dict_file.read())

    with open("data/patients_1_context.txt", "r") as context_file:
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

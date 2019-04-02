import json
from urllib.parse import quote

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


def jsonldify_row(row, column, data_type_dict, _id_key="_id",
                       _type_key="_type", _label_key="_label", data_key="has_row"):
    ## add table iri to json
    # json_data = json_update(row, _id_key, table_iri)
    json_data = \
    {
        f"{_id_key}": f"""{data_type_dict["i"]["table"]["iri"]}""",
        f"{data_key}": json_as_dict(row[column])
    }

    ## add row type to json (goes into the block after the data_key)
    row_type = data_type_dict["i"]["row"]["type"]
    json_data = json_update(json_data, update_key=_type_key, update_value=row_type, data_key=data_key)

    ## add row id
    row_id = data_type_dict["i"]["row"]["ns"] + "row_" + str(row.name)  # build id
    json_data = json_update(json_data, update_key=_id_key, update_value=row_id, data_key=data_key)

    ## add row label
    row_label = data_type_dict["i"]["table"]["table_name"] + ".row_" + str(row.name)  # build label
    json_data = json_update(json_data, update_key=_label_key, update_value=row_label, data_key=data_key)

    return json_data


def jsonldify_fields(df, jsonld_column_name, data_type_dict, _id_key="_id",
                        _type_key="_type", _label_key="_label", data_key="has_row"):
    def update_data(data, udate_key, update_value):
        ## if data is in a list; update each item;
        ## json_update returns a string (i.e., json) so use loads to convert to a dict
        if type([]) == type(data):
            new_data = \
                list(map(lambda d: json.loads(json_update(d, udate_key, update_value)), data))
        else:
            new_data = \
                json.loads(json_update(data, udate_key, update_value))
        return new_data

    fields = data_type_dict["i"]["field"]["subtype"] # get field dict from the type dict
    for idx, json_data in df[[jsonld_column_name]].itertuples(): # get the index and jason data from df
        jdata = json_as_dict(json_data) # convert json data to dictionary
        for field in fields:
            field_data = jdata[data_key][field] # get data for the particular data field
            field_type = fields[field]["type"]  # get the field type of the data field instance
            field_data = update_data(field_data, _type_key, field_type) # add field type info

            ## add id for the field instance
            field_id = data_type_dict["i"]["field"]["ns"] + "row_" + str(idx) + "." + quote(field)  # build id
            field_data = update_data(field_data, _id_key, field_id)

            ## add label for the field insance
            field_label = data_type_dict["i"]["table"]["table_name"] + ".row_" + str(idx) + "." + field  # build label
            field_data = update_data(field_data, _label_key, field_label)

            # print(field_data)
            ## update the info for the field with new field data
            jdata["has_row"][field] = field_data
            df.at[idx, jsonld_column_name] = json.dumps(jdata) # update data frame

    return df[jsonld_column_name]


def json_as_dict(json_data, data_key=None):
    if data_key:
        return json.loads(json_data)[data_key]
    else:
        return json.loads(json_data)


def json_update(json_data, update_key, update_value, data_key=None):
    # load json data into dict
    if type({}) == type(json_data):
        jdata = json_data
    else:
        jdata = json_as_dict(json_data)
    if data_key:
        jdata[data_key].update({f"{update_key}": f"{update_value}"})
    else:
        jdata.update({f"{update_key}": f"{update_value}"})  # add key:value info

    # print('jdata: ', json_data, ' type: ', type(jdata), ' data_key: ', data_key)
    return json.dumps(jdata)


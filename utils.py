import csv
import os
from decimal import Decimal
from collections import defaultdict, OrderedDict
import jinja2

import sass

def get_base_path():
    return os.path.dirname(__file__)

def get_jinja_template_env():
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(get_base_path()))

def get_css():
    return sass.compile(filename="assets/report.sass")

def get_csv_file(report_name, period=None):
    return read_csv_file(f"{get_base_path()}/{(period or 'week')}_data/{report_name}.csv")

def group_dz_locations(period=None):
    (locations, headers) = get_csv_file('origin_dz', period='week')
    grouped = {}

    for location in locations:
        if (location["country"] not in grouped):
            grouped[location["country"]] = []

        if (location["region"] not in grouped[location["country"]]):
            grouped[location["country"]].append(location)    

    return grouped, locations, headers

def group_locations(period=None):
    (locations, headers) = get_csv_file('origin', period=period)
    grouped = defaultdict(list)

    for location in locations:
        if (location["zone"] not in grouped):
            grouped[location["zone"]] = {}

        if (location["region"] not in grouped[location["zone"]]):
            grouped[location["zone"]][location["region"]] = []

        grouped[location["zone"]][location["region"]]\
            .append(location)

    return grouped, locations, headers

def read_csv_file(csv_file):
    csv_list = None

    if (csv_file is not None):
        with open(csv_file) as csv_file_obj:
            reader = csv.DictReader(csv_file_obj)
            csv_list = list(reader)

    return (csv_list, reader.fieldnames)

def get_total_row(rows, group_by_column='store'):
    total_row = {}

    scanning = True
    scanning_level = 1
    while scanning:
        for row in rows:
            for column in row.keys():
                if column in ('level', group_by_column):
                    total_row[column] = ''
                else:
                    if row.get('level') == scanning_level:
                        try:
                            total_row[column] += Decimal(row[column] or '0.0')
                        except:
                            total_row[column] = Decimal(row[column] or '0.0')

        if total_row.get(column) is None:
            scanning_level = 2
        else:
            scanning = False

    total_row[group_by_column] = "Grand Total"
    total_row["level"] = 100

    return total_row

def sort_by_column(report_name, groupings, rows, group_by_column='store'):
    sorted_rows = []

    for zone in sorted(groupings.keys()):

        for row in rows:
            group_by = row[group_by_column]

            if group_by.lower() == zone.lower():
                if 'level' not in row:
                    row['level'] = 1
                    sorted_rows.append(row)
                    break

        if type(groupings[zone]) == dict:
            for region in sorted(groupings[zone].keys()):
                for row in rows:
                    group_by = row[group_by_column]

                    if group_by.lower() == region.lower() == zone.lower():
                        if 'level' not in row:
                            row['level'] = 2
                            sorted_rows.append(row)

                    elif group_by.lower() == region.lower():
                        if 'level' not in row:
                            row['level'] = 2
                            sorted_rows.append(row)

                for location in sorted(groupings[zone][region], key=lambda x: x['legacy_id']):
                    for row in rows:
                        group_by = row[group_by_column]
                        
                        if group_by.lower() == location.get('legacy_id', '').lower():
                            if 'level' not in row:
                                row['level'] = 3
                                sorted_rows.append(row)
        else:
            for location in sorted(groupings[zone], key=lambda x: x['country']):
                for row in rows:
                    group_by = row[group_by_column]
                    
                    if group_by.lower() == location.get('region').lower():
                        if 'level' not in row:
                            row['level'] = 3
                            sorted_rows.append(row)

    # for i, row in enumerate(sorted_rows):
    #     for j, similar_row in enumerate(sorted_rows):
    #         if i == j:
    #             continue
    #         else:
    #             if row == similar_row:
    #                 continue
    #             elif row[group_by_column] == similar_row[group_by_column]:
    #                 if row['level'] == similar_row['level']:
    #                     similar_row['level'] += 1
    #                     print('row', row, similar_row)
    #                     break

    return sorted_rows

def get_full_report_name(report_name):
    full_names = {
        'dpp': "Average Unit Sales per Store", 
        'dpt': "Average Order Sales per Store", 
        'upt': "UPT", 
        'tphw': "Traffic per Worked Hours", 
        'sphw': "Sales per Worked Hours", 
        'payments': "Retail Sales $(CAD) Per Store", 
        'traffic': "Retail Traffic per Store",
        'orders': "Retail Orders per Store",
        'products': "Products", 
        'summary': "Summary",
        'dz_orders': "Consumer Sales in unit per Delivery Region and Channel", 
        'dz_payments': "Consumer Sales in $(CAD) per Delivery Region and Channel", 
    }
    if report_name is not None:
        return full_names.get(report_name)
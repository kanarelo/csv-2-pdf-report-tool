import csv
from collections import OrderedDict

from decimal import Decimal
from utils import sort_by_column, \
    read_csv_file, get_csv_file, group_locations, \
    get_full_report_name, group_dz_locations, \
    get_total_row, get_comparables_total_row, get_comparable_rows

def generate_budget_report_from_csv(
    report_name, 
    dz=False,
    period='week',
    header_name=None,
    group_by_column='store',
    label_column='store',
    totalled_reports=None,
    comparable_reports=None
):
    (rows, headers) = get_csv_file(report_name, period=period)
    display_header_groupings = {}

    if group_by_column is not None:
        if dz:
            (groupings, locations, origin_headers) = group_dz_locations(period=period)
        else:
            (groupings, locations, origin_headers) = group_locations(period=period)

        rows = sort_by_column(groupings, rows, group_by_column=group_by_column)

    display_headers = [
        header 
            for header in headers
                if header not in (label_column, 'level')]

    grayed_columns = []
    _dict = []
    if dz:
        if ('retail_orders' in ",".join(display_headers)) or ('retail_sales' in ",".join(display_headers)):
            _dict += [
                ({
                    'webcs': 'Web', 
                    'retail': 'Retail', 
                    'total': 'Total'
                }.get(item), (
                        [x for x in display_headers if x.startswith('retail_')],
                        sum(1 for x in display_headers if x.startswith('retail_'))
                )) for item in ('retail', 'webcs', 'total')]
    else:
        if 'budget_' in ",".join(display_headers):
            filter_by = report_name
            if report_name == 'payments':
                filter_by = 'sales'

            header_meta = \
                ('Budget', (
                    [x for x in display_headers if x.startswith('budget_%s' % filter_by)],
                    sum(1 for x in display_headers if x.startswith('budget_%s' % filter_by))))

            (_, (_headers, _)) = header_meta
            grayed_columns += [i for i in _headers if i != max(_headers)]
            _dict.append(header_meta)

            if header_name is not None:
                if header_name in ",".join(display_headers):
                    header_meta = (
                        'Actual', (
                            [x for x in display_headers if x.startswith(header_name)],
                            sum(1 for x in display_headers if x.startswith(header_name))))

                    (_, (_headers, _)) = header_meta
                    _dict.append(header_meta)
                    grayed_columns += [i for i in _headers if i != max(_headers)]
            else:
                if report_name in ",".join(display_headers):
                    header_meta = (
                        'Actual', (
                            [x for x in display_headers if x.startswith(report_name)],
                            sum(1 for x in display_headers if x.startswith(report_name))))

                    (_, (_headers, _)) = header_meta
                    _dict.append(header_meta)
                    grayed_columns += [i for i in _headers if i != max(_headers)]

            if 'budget_diff' in display_headers:
                _dict.append(('Actual vs Budget', (['budget_diff'], 1)))

            if 'yoy' in display_headers:
                _dict.append(('YOY', (['yoy'], 1)))
        # else:
        #     (_, (_headers, _)) = header_meta
        #     _dict.append(header_meta)
        #     grayed_columns += [i for i in _headers if i != max(_headers)]

    if _dict:
        display_header_groupings = OrderedDict(_dict)
    
    if totalled_reports and (report_name in totalled_reports):
        total_row = get_total_row(rows, group_by_column=group_by_column)
        rows.append(total_row)

    if not dz:
        if comparable_reports and (report_name in comparable_reports):
            comparable_rows = list(get_comparable_rows(
                rows, 
                group_by_column=group_by_column, 
                groupings=groupings, 
                period=period,
                row_headers=headers,
                report_name=report_name,
                origin_headers=origin_headers))
    
            if comparable_rows:
                total_comparable_row = get_comparables_total_row(comparable_rows, headers)
    
                rows.append(total_comparable_row)
                rows += comparable_rows

    return (rows, display_headers, display_header_groupings, grayed_columns)

def generate_summary_report_from_csv(period='week'):
    (rows, headers) = get_csv_file('summary', period=period)
    (groupings, locations, origin_headers) = group_locations()

    sorted_rows = sort_by_column(groupings, rows, group_by_column='store')
    grand_total = next(x for x in rows if x['store'] == "Grand_Total")

    sorted_rows.append({
        "store": "Grand Total",
        "level": 100,
        "traffic": grand_total["traffic"],
        "orders": grand_total["orders"],
        "conversion": grand_total["conversion"],
        "sales": grand_total["sales"],
        "dpt": grand_total["dpt"],
        "units": grand_total["units"],
        "upt": grand_total["upt"],
        "tphw": grand_total["tphw"],
        "sphw": grand_total["sphw"]})

    return sorted_rows

def generate_report_context(report_name, period=None, totalled_reports=None, comparable_reports=None):
    context = {
        'report_name': report_name, 
        'full_report_name': get_full_report_name(report_name)}
    template_name = (report_name and ("%s.html" % report_name) or "summary.html")
    
    if period is not None:
        context['period'] = period

    if report_name == 'summary':
        context['rows'] = generate_summary_report_from_csv(period=period)
    elif report_name in (
        'dpp', 'dpt', 
        'upt', 'tphw', 
        'sphw', 'payments', 
        'traffic', 'orders',
        'products', 
        'dz_orders', 'dz_payments'
    ):  
        header_name = group_by_column = label_column = None
        dz = False

        context['decimal_places'] = 2
        context['suffix'] = ''
        if report_name in ('orders', 'products', 'tphw', 'traffic', 'dz_orders', 'upt'):
            context['prefix'] = ''

            if report_name == 'tphw':
                context['prefix'] = ''
            elif report_name == 'upt':
                context['decimal_places'] = 2
            else:
                context['decimal_places'] = 0
        else:
            context['prefix'] = '$'

        if report_name in ('dz_orders', 'dz_payments'):
            (header_name, label_column, group_by_column) = ('retail_orders', 'district', 'district')
            dz = True
        else:
            group_by_column = label_column = 'store'
        
            if report_name == 'traffic':
                header_name = 'visits'
            elif report_name == 'payments':
                header_name = 'sales'
            elif report_name == 'products':
                header_name = 'quantity'
        
        context['label_column'] = label_column
        context['rows'], \
        context['display_headers'], \
        context['display_header_groupings'], \
        context['grayed_columns'] = \
            generate_budget_report_from_csv(
                report_name, 
                dz=dz,
                period=period,
                header_name=header_name, 
                label_column=label_column,
                totalled_reports=totalled_reports,
                comparable_reports=comparable_reports,
                group_by_column=group_by_column)
        
        template_name = "budget_report.html"

    return (template_name, context)

import json
import gspread
import re

cred_path = "/etc/opt/django_app/service.key"
gc = gspread.service_account(filename=cred_path)

def _get_sheet(id, name):
    return gc.open_by_key(id).worksheet(name)

def get_list(id, name, cols=False, range_name=None, *args, **kwargs):
    sh = _get_sheet(id, name)
    if cols:
        return sh.get_values(range_name, major_dimension="COLUMNS")
    else:
        return sh.get_values(range_name)

def append_row(id, name, data, value_input_option='RAW', *args, **kwargs):
    sh = _get_sheet(id, name)
    result = sh.append_row(data, value_input_option=value_input_option)
    urange = result['updates']['updatedRange']
    row = int(re.search(r'\d+', urange).group())
    return {'row': row}

def append_rows(id, name, data, value_input_option='RAW', *args, **kwargs):
    if isinstance(data, str):
        data = json.loads(data)
    sh = _get_sheet(id, name)
    result = sh.append_rows(data, value_input_option=value_input_option)
    rows = result['updates']['updatedRows']
    return {'rows': rows}

def find(id, name, query, in_row=None, in_column=None, get_row=False, get_col=False, case_sensitive=True, *args, **kwargs):
    if isinstance(in_column, str):
        in_column = gspread.utils.column_letter_to_index(in_column)
    sh = _get_sheet(id, name)
    data = sh.find(query, in_row, in_column, case_sensitive)
    if data is None:
        return None
    if get_row and get_col:
        raise NotImplementedError
    if get_row:
        raise NotImplementedError
    if get_col:
        raise NotImplementedError
    return (data.row, data.col)

def find_all(id, name, query, in_row=None, in_column=None, get_rows=False, get_cols=False, ret_col = None, ret_row = None, case_sensitive=True, *args, **kwargs):
    if isinstance(in_column, str):
        in_column = gspread.utils.column_letter_to_index(in_column)
    sh = _get_sheet(id, name)
    data = sh.findall(query, in_row, in_column, case_sensitive)
    cells = [(cell.row, cell.col) for cell in data]
    result = {'cells': cells}
    if get_rows:
        if len(cells):
            rquery = [':'.join([str(cell[0])] * 2) for cell in cells]
            rows = sh.batch_get(rquery)
            result['rows'] = [row[0] for row in rows]
        else:
            result['rows'] = []
    if get_cols:
        raise NotImplementedError
    if ret_row is not None:
        raise NotImplementedError
    if ret_col is not None:
        if len(cells):
            unique_rows = set()
            for cell in cells:
                unique_rows.add(cell[0])
            unique_rows = sorted(unique_rows)
            rquery = [':'.join([ret_col + str(row)] * 2) for row in unique_rows]
            ret_cols = sh.batch_get(rquery)
            result['ret_cols'] = [cell[0][0] for cell in ret_cols]
        else:
            result['ret_cols'] = []
    return result

def get_unique(id, name, col = None, row = None, start_row = "", start_col = "", *args, **kwargs):
    if col is None and row is None:
        raise ValueError('Please specify row or column')
    if col is not None and row is not None:
        raise ValueError('Please specify only row or column')
    sh = _get_sheet(id, name)
    if row is not None:
        qrange = start_col + str(row) + ':' + str(row)
        data = sh.get(qrange)[0]
        result = set()
        for d in data:
            result.add(d)
    if col is not None:
        qrange = col + str(start_row) + ':' + col
        data = sh.get(qrange, major_dimension="COLUMNS")[0]
        result = set()
        for d in data:
            result.add(d)
    return sorted(result)

def update_cells(id, name, cells, values, value_input_option='RAW', *args, **kwargs):
    if not isinstance(cells, list):
        raise ValueError('Cells must be an array')
    if not isinstance(values, list):
        raise ValueError('Values must be an array')
    if len(cells) > len(values):
        raise ValueError('Please specify values for all cells')
    prepared_cells = []
    for i in range(len(cells)):
        if isinstance(cells[i], str):
            prepared_cells.append(gspread.cell.Cell.from_address(cells[i], values[i]))
        else:
            prepared_cells.append(gspread.cell.Cell(*cells[i], values[i]))
    
    sh = _get_sheet(id, name)
    sh.update_cells(prepared_cells, value_input_option)
    return True

def update(id, name, data, range_name = None, *args, **kwargs):
    sh = _get_sheet(id, name)
    if (range_name):
        sh.update(range_name, data, **kwargs)
    else:
        sh.update(data, **kwargs)
    return True

if __name__ == "__main__":
    cred_path = "google_helper/service.key"

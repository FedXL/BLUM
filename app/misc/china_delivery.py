import google_helper.sheets as sheets
from telegram_helper.telegram import batch_send_unique
from telegram_helper.telegram import send_message
from telegram_helper.telegram import send_message_split
import json
from datetime import datetime, timedelta
from threading import Thread
from time import sleep

def get_status(sheet_id, sheet_name, client_id, settings_name, bot_token=None, timeout=0.3, *args, **kwargs):
	tracked = sheets.get_list(sheet_id, sheet_name, True)
	result = []
	for i, j in enumerate(tracked[1]):
		if j == client_id:
			result.append([col[i] for col in tracked])
	message = status_to_text(result, sheet_id, settings_name)
	if bot_token is not None:
		result = send_message_split(bot_token, client_id, message, timeout, *args, **kwargs)
		return result
	return message

def status_to_text(statuses, sheet_id, settings_name):
	settings = sheets.get_list(sheet_id, settings_name, True)
	cl_phrase = settings[3][1:]
	status = settings[9][1:11]
	result = ''
	for status_line in statuses:
		curr_status = status_line[2]
		if (curr_status == status[0]):
			result += cl_phrase[8] + " " + status_line[0] + " " + cl_phrase[13]
		elif (curr_status == status[1] or \
			curr_status == status[2] or \
			curr_status == status[3]):
			result += cl_phrase[9] + " " + status_line[0] + " " + cl_phrase[14]
			#Date
			if (status_line[5]):
				result += " " + status_line[5]
			else:
				result += " " + '.'.join(status_line[3].split(' ')[0].split('-')[::-1])
		elif (curr_status == status[4] or \
			curr_status == status[5] or \
			curr_status == status[6]):
			result += cl_phrase[10] + " " + status_line[0] + " " + cl_phrase[15]
			#Date
			if (status_line[5]):
				result += " " + status_line[5]
			else:
				result += " " + '.'.join(status_line[3].split(' ')[0].split('-')[::-1])
		elif (curr_status == status[7] or \
			curr_status == status[8] or \
			curr_status == status[9]):
			result += cl_phrase[11] + " " + status_line[0] + " " + cl_phrase[16]
			#Date
			if (status_line[5]):
				result += " " + status_line[5]
			else:
				result += " " + '.'.join(status_line[3].split(' ')[0].split('-')[::-1])
		else:
			result += cl_phrase[12] + " " + status_line[0] + " " + cl_phrase[17]
		result += "\n"
	if result == "":
		result = cl_phrase[18]
	return result

def check_client(sheet_id, sheet_name, client_id, *args, **kwargs):
	clients = sheets.get_list(sheet_id, sheet_name, True)
	return client_id in clients[0]

def add_tracks(sheet_id, sheet_name, client_id, query, *args, **kwargs):
	query = query.upper().strip()
	lines = [line.strip() for line in query.split('\n')]
	lines = set(lines)
	total_cnt = len(lines)
	accepted = []
	rejected = []
	found = []
	tracked = sheets.get_list(sheet_id, sheet_name, True)
	tracks = set([track.upper() for track in tracked[0]])
	for line in lines:
		if line in tracks:
			found.append(line)
		elif len(line) < 10 or len(line) > 50:
			rejected.append(line)
		else:
			accepted.append(line)
	if len(accepted):
		date = (datetime.utcnow() + timedelta(hours=5)) \
			.isoformat() \
			.replace('T', ' ')
		date = date[:date.rfind('.')]
		to_append = []
		for track in accepted:
			to_append.append([track, client_id, "WAITING", date])
		sheets.append_rows(sheet_id, sheet_name, to_append, "USER_ENTERED")
	return {
		"total": total_cnt,
		"rejected": rejected,
		"found": found
	}

def update_table(sheet_id, table_name, client_name, tracked_name, new_status, status_list, *args, **kwargs):
	try:
		table = sheets.get_list(sheet_id, table_name)
		clients = sheets.get_list(sheet_id, client_name, True)
		tracked = sheets.get_list(sheet_id, tracked_name, True)
		track_dict = dict([(track, i) for i, track in enumerate(tracked[0])])
		client_dict = dict([(client, i) for i, client in enumerate(clients[0])])
		date = (datetime.utcnow() + timedelta(hours=5)) \
			.isoformat() \
			.replace('T', ' ')
		date = date[:date.rfind('.')]
		cells = []
		values = []
		tr_cells = []
		tr_values = []
		for i, row in enumerate(table[1:], 2):
			track = track_dict.get(row[0], -1)
			cells.append([i, 5])
			values.append(date)
			if track == -1:
				cells.append([i, 6])
				values.append("Нет данных")
				continue
			tr_status = -1
			try:
				tr_status = status_list.index(tracked[2][track])
			except:
				pass
			if new_status > tr_status:
				tr_cells.append([track + 1, 3])
				tr_values.append(status_list[new_status])
				tr_cells.append([track + 1, 4])
				tr_values.append(date)
			if new_status >= tr_status and row[1] != '':
				tr_cells.append([track + 1, 6]);
				tr_values.append(row[1]);
			cl_row = client_dict.get(tracked[1][track], -1)
			if cl_row == -1:
				cells.append([i, 6])
				values.append("Нет данных")
				continue
			cells.append([i, 3])
			values.append(clients[1][cl_row])
			cells.append([i, 4])
			values.append(clients[2][cl_row])
			if new_status >= tr_status:
				cells.append([i, 6])
				values.append("Не доставлено")
			elif new_status + 1 == tr_status:
				cells.append([i, 6])
				values.append("Доставлено")

		if len(cells):
			sheets.update_cells(sheet_id, table_name, cells, values, "USER_ENTERED")
		if len(tr_cells):
			sheets.update_cells(sheet_id, tracked_name, tr_cells, tr_values, "USER_ENTERED")
		return True
	except:
		return False

def send_notifications(sheet_id, table_name, client_name, tracked_name, new_status, status_list, phrases, bot_token, operator_id=None, *args, **kwargs):
	try:
		table = sheets.get_list(sheet_id, table_name)
		clients = sheets.get_list(sheet_id, client_name, True)
		tracked = sheets.get_list(sheet_id, tracked_name, True)
		track_dict = dict([(track, i) for i, track in enumerate(tracked[0])])
		client_dict = dict([(client, i) for i, client in enumerate(clients[0])])
		date = (datetime.utcnow() + timedelta(hours=5)) \
			.isoformat() \
			.replace('T', ' ')
		date = date[:date.rfind('.')]
		cells = []
		values = []
		tr_cells = []
		tr_values = []
		other_cells = []
		other_values = []
		other_tr_cells = []
		other_tr_values = []
		tg_ids = []
		tr_nums = []
		date_to_send = []
		for i, row in enumerate(table[1:], 2):
			track = track_dict.get(row[0], -1)
			if track == -1:
				continue
			tr_status = -1
			try:
				tr_status = status_list.index(tracked[2][track])
			except:
				pass
			if tr_status == -1 or ( \
					new_status + 1 >= tr_status and \
					new_status != tr_status):
				other_cells.append([i, 5])
				other_values.append(date)
				cells.append([i, 6])
				tg_ids.append(tracked[1][track])
				tr_nums.append(row[0])
				tr_cells.append([track + 1, 3])
				tr_values.append(status_list[new_status])
				tr_cells.append([track + 1, 4])
				tr_values.append(date)
				if row[1] != '':
					date_to_send.append(row[1])
					if tracked[5][track] != row[1]:
						other_tr_cells.append([track + 1, 6]);
						other_tr_values.append(row[1]);
				elif tracked[5][track]:
					date_to_send.append(tracked[5][track])
				else:
					date_to_send.append('.'.join(tracked[3][track].split(' ')[0].split('-')[::-1]))
		def update():
			if len(tg_ids):
				messages = []
				for i, tg_id in enumerate(tg_ids):
					text = phrases[0] + ' '
					text += tr_nums[i] + ' '
					text += phrases[1] + ' '
					text += date_to_send[i]
					if new_status == 8:
						text += phrases[2]
					messages.append(text)
				send_status = batch_send_unique(bot_token, tg_ids, messages, **kwargs)
				for i, successful in enumerate(send_status):
					if successful:
						values.append("Доставлено")
					else:
						values.append("Не доставлено")
						tr_values[i * 2] = status_list[new_status + 1]

			if len(cells) or len(other_cells):
				sheets.update_cells(sheet_id, table_name, [*cells, *other_cells], [*values, *other_values], "USER_ENTERED")
			if len(tr_cells) or len(other_tr_cells):
				sheets.update_cells(sheet_id, tracked_name, [*tr_cells, *other_tr_cells], [*tr_values, *other_tr_values], "USER_ENTERED")

			if operator_id is not None:
				send_message(bot_token, operator_id, "Рассылка завершена. Вы можете запустить следующую рассылку")

		Thread(target=update).start()

		return len(tg_ids)
	except Exception as e:
		print(e)
		return -1

import pandas as pd
from models.WorkerStatus import WorkerStatus, make_worker_object_from_dataframe
from datetime import datetime
from plotly.subplots import make_subplots
import plotly.figure_factory as ff

def process_df_for_gantt(df:pd)  :
    # result = [f(row[0], ..., row[5]) for row in df[['host_ip','filename','function_name','action','column_name','timestamp']].to_numpy()]
    # print(result)
    workerstatus_list= make_worker_object_from_dataframe(df)

    # process timestamp into linear 
    # find min
    #combine task from
    worker_dict={}
    key_start = 'start'
    key_end = 'end'
    key_task = 'task'
    key_host_ip = 'host_ip'
    for worker in workerstatus_list:
        host_ip = (worker.host_ip)
        task_id =  (worker.task_id)
        if host_ip in worker_dict:
    
            if task_id in worker_dict[host_ip]:
                # print(f"exit {task_id} in {host_ip}")
                if key_start in worker_dict[host_ip][task_id]:
                    worker_dict[host_ip][task_id][key_end] = worker.time
                else:
                    worker_dict[host_ip][task_id][key_start] = worker.time
                # get duration from datetime
                end = pd.to_datetime( worker_dict[host_ip][task_id][key_end])
                start= pd.to_datetime( worker_dict[host_ip][task_id][key_start])
                worker_dict[host_ip][task_id]['duration'] = int(round((end - start).total_seconds()))

            else:
                # print(f"add new task {task_id}")
                temp_dict = {}
                worker_dict[host_ip][task_id] = {}
                if pd.isnull(worker.filename):
                    temp_dict[key_task] = worker.function_name
                else:
                    temp_dict[key_task] = worker.filename
              
                if worker.action == "busy-stop/idle-start":
                    temp_dict[key_end] = worker.time
                else:
                    temp_dict[key_start] = worker.time
                worker_dict[host_ip][task_id] = temp_dict

        else:
            info_dict = {}
            worker_dict[host_ip] = {}
            if pd.isnull(worker.filename):
                info_dict[key_task] = worker.function_name
            else:
                info_dict[key_task] = worker.filename
            if worker.action == "busy-stop/idle-start":
                info_dict[key_end] = worker.time
            else:
                info_dict[key_start] = worker.time

            worker_dict[host_ip][task_id] =info_dict
    # for worker in workerstatus_list:
    #     # print(worker.task_id)
    #     task_id = worker.task_id
    #     if task_id in worker_dict:
            # if key_start in worker_dict[task_id]:
            #     worker_dict[task_id][key_end] = worker.time
            # else:
            #     worker_dict[task_id][key_start] = worker.time
            # # get duration from datetime
            # end = pd.to_datetime( worker_dict[task_id][key_end])
            # start= pd.to_datetime( worker_dict[task_id][key_start])
            # worker_dict[task_id]['duration'] = int(round((end - start).total_seconds()))
  
            # # duration = float(worker_dict[task_id][key_end]) - float(worker_dict[task_id][key_start])
            # # worker_dict[task_id]['duration'] = duration
           
    #     else:
            # info_dict = {}
            # if pd.isnull(worker.filename):
            #     info_dict[key_task] = worker.function_name
            # else:
            #     info_dict[key_task] = worker.filename
            # # print(info_dict['task'])
            # info_dict[key_host_ip] = worker.host_ip
            # if worker.action == "busy-stop/idle-start":
            #     info_dict[key_end] = worker.time
            # else:
            #     info_dict[key_start] = worker.time
            # worker_dict[worker.task_id] = info_dict
    
    # for key in worker_dict:
    #     print(f" key :{key}")


    return worker_dict

# def addAnnot(df, fig):
#     for i in df:
#         x_pos = (i['Finish'] - i['Start'])/2 + i['Start']
#         for j in fig['data']:
#             if j['name'] == i['Label']:
#                 y_pos = (j['y'][0] + j['y'][1] + j['y'][2] + j['y'][3])/4
#         fig['layout']['annotations'] += tuple([dict(x=x_pos,y=y_pos,text=i['Label'],font={'color':'black'})])


def process_logs():
    print('process_logs')
    df = pd.read_csv('logs.csv', index_col=0, parse_dates=['timestamp'], infer_datetime_format=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'], 
                                  unit='s')

    worker_dict = process_df_for_gantt(df)

    # # # Show dataframe
    figures = []
    subplot_titles = []
    for key , value in worker_dict.items():
        gantt_list = []
        subplot_titles.append(key)
        for k2,v2 in value.items():
            item = dict(Task=v2['task'], Start=(v2['start']), Finish=(v2['end']), Resource=f"{v2['task']}:{v2['duration']}s", Duration = v2['duration'])
    #     print(item)
            gantt_list.append(item)
        gantt_df = pd.DataFrame(gantt_list)
        
        fgg = ff.create_gantt(gantt_df, reverse_colors=True, show_colorbar=True,index_col='Resource')
        figures.append(fgg)
      
    figs = make_subplots(rows=len(figures), cols=1,
                    shared_xaxes=True,subplot_titles = subplot_titles)
    row = 1
    for fgg in figures:
        figs['layout'][f'yaxis{row}'].update(fgg.layout.yaxis)
        for trace in fgg.data:
            figs.add_trace(trace, row=row, col=1)
        row += 1
    figs.update_layout(
        xaxis = dict(
            tickmode = 'linear',
            tick0 = 0.5,
            dtick = 2
        )
    )
    figs.show()

import pandas as pd
from models.WorkerStatus import WorkerStatus, make_worker_object_from_dataframe
from datetime import datetime
from utils.eks_utils import match_pod_ip_to_node_name
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import plotly.express as px
import plotly.io as pio
from utils.aws_utils import(
    connect_aws_client,
    read_all_csv_from_s3_and_parse_dates_from

)
def process_df_for_gantt_separate_worker(df:pd)  :
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

def process_logs_subplot():
    print('process_logs')
    df = pd.read_csv('logs.csv', index_col=0, parse_dates=['timestamp'], infer_datetime_format=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'], 
                                  unit='s')

    worker_dict = process_df_for_gantt_separate_worker(df)

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
    key_pid = 'pid'
    for worker in workerstatus_list:
        # print(worker.task_id)
        task_id = worker.task_id
        if task_id in worker_dict:
            if key_start in worker_dict[task_id]:
                worker_dict[task_id][key_end] = worker.time
            else:
                worker_dict[task_id][key_start] = worker.time
            # get duration from datetime
            end = pd.to_datetime( worker_dict[task_id][key_end])
            start= pd.to_datetime( worker_dict[task_id][key_start])
            worker_dict[task_id]['duration'] = int(round((end - start).total_seconds()))
  
            # duration = float(worker_dict[task_id][key_end]) - float(worker_dict[task_id][key_start])
            # worker_dict[task_id]['duration'] = duration
           
        else:
            info_dict = {}
            if pd.isnull(worker.filename):
                info_dict[key_task] = worker.function_name
            else:
                info_dict[key_task] = worker.filename
            # print(info_dict['task'])
            info_dict[key_host_ip] = worker.host_ip
            info_dict[key_pid] = worker.pid
            if worker.action == "busy-stop/idle-start":
                info_dict[key_end] = worker.time
            else:
                info_dict[key_start] = worker.time
            worker_dict[worker.task_id] = info_dict
    
    # for key in worker_dict:
    #     print(f" v --->:{worker_dict[key]['host_ip']}")


    return worker_dict

# def addAnnot(df, fig):
#     for i in df:
#         x_pos = (i['Finish'] - i['Start'])/2 + i['Start']
#         for j in fig['data']:
#             if j['name'] == i['Label']:
#                 y_pos = (j['y'][0] + j['y'][1] + j['y'][2] + j['y'][3])/4
#         fig['layout']['annotations'] += tuple([dict(x=x_pos,y=y_pos,text=i['Label'],font={'color':'black'})])


def process_logs_from_local():



    print('process_logs')
    df = pd.read_csv('logs.csv', index_col=0, parse_dates=['timestamp'], infer_datetime_format=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'], 
                                  unit='s')
    # match pod id to node name
    pods_name_prefix_set = ("worker", "webapp")
    pods_info_dict = match_pod_ip_to_node_name(pods_name_prefix_set)
    worker_dict = process_df_for_gantt(df)
    # atlter ip to host name


    # # # # Show dataframe

    gantt_list = []
    for key , value in worker_dict.items():
        # print(f"{value} ")
        # print(f"start :{value['start']} end:{value['end']}")
        pod_ip = value['host_ip']
        node_name = ""
        # get node name
        if pod_ip in pods_info_dict:
            node_name = pods_info_dict[pod_ip]['NOD_NAME']

        task = f"{node_name}: {value['host_ip']}: {value['pid']}"
        label = f"{value['task']}: duration:{value['duration']}s"
        item = dict(Task=task, 
        Start=(value['start']), 
        Finish=(value['end']), 
        Resource=value['task'],
        Node = node_name,
        Label=label,
        Host=value['host_ip'], 
        Duration = value['duration'])
        gantt_list.append(item)
    gantt_df = pd.DataFrame(gantt_list)
    fig = px.timeline(gantt_df, x_start="Start", x_end="Finish", y="Task",color="Node", text="Label")
    fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
    fig.show()


def process_logs_from_s3(bucket, logs_file_path_name, saved_image_name, s3_client):

    df = read_all_csv_from_s3_and_parse_dates_from(bucket_name=bucket,
                                file_path_name=str(logs_file_path_name), 
                                dates_column_name = "timestamp",
                                s3_client=s3_client)


    pods_name_prefix_set = ("worker", "webapp")
    pods_info_dict = match_pod_ip_to_node_name(pods_name_prefix_set)
    worker_dict = process_df_for_gantt(df)
    # atlter ip to host name
    # print(worker_dict)
    # # # # Show dataframe

    gantt_list = []
    for key , value in worker_dict.items():
        # print(f"{value} ")
        # print(f"start :{value['start']} end:{value['end']}")
        pod_ip = value['host_ip']
        node_name = ""
        # get node name
        if pod_ip in pods_info_dict:
            node_name = pods_info_dict[pod_ip]['NOD_NAME']

        task = f"{node_name}: {value['host_ip']}: {value['pid']}"
        label = f"{value['task']}: duration:{value['duration']}s"
        item = dict(Task=task, 
        Start=(value['start']), 
        Finish=(value['end']), 
        Resource=value['task'],
        Node = node_name,
        Label=label,
        Host=value['host_ip'], 
        Duration = value['duration'])
        gantt_list.append(item)
    gantt_df = pd.DataFrame(gantt_list)
    fig = px.timeline(gantt_df, x_start="Start", x_end="Finish", y="Task",color="Node", text="Label")
    fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
    # fig.show()
    image_name ="test.png"
    pio.write_image(fig, image_name, format="png", scale=1, width=2400, height=1600) 

    img_data = open( image_name, "rb")
    s3_client.put_object(Bucket=bucket, Key=saved_image_name, Body=img_data, 
                                 ContentType="image/png")


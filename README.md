# gismo-cloud-deploy


## Start the project 

### local development

1. Init server by docker-compose
~~~
cd gismoclouddeploy/services/
docker-compose up --build
~~~
Check server is running by: http://localhost:5010/solardata/ping/ on browser
You should see:
~~~
{
  "container_id": "e7097b1122ad", 
  "message": "pong!", 
  "status": "success"
}
~~~


2. Init database. Open another terminal window.
   
~~~
cd gismoclouddeploy/services/
docker-compose exec web python app.py recreate_db
docker-compose exec web python app.py seed_db
~~~
Check db had seed data by running: http://localhost:5010/solardata/all_results/ on browser
You shoud see:
~~~

{
  "container_id": "e7097b1122ad", 
  "solardata": [
    {
      "bucket_name": "pv.insight.nrel", 
      "capacity_changes": false, 
      "capacity_estimate": 5.28, 
      "column_name": "Power(W)", 
      "data_clearness_score": 31.8, 
      "data_quality_score": 98.4, 
      "data_sampling": 5, 
      "error_message": "this is test error message", 
      "file_name": "10059.csv", 
      "file_path": "PVO/PVOutput", 
      "id": 1, 
      "inverter_clipping": false, 
      "length": 4.41, 
      "normal_quality_scores": true, 
      "num_clip_points": 0, 
      "power_units": "W", 
      "process_time": 23.23, 
      "task_id": "task_id", 
      "time_shifts": false, 
      "tz_correction": -1
    }
  ], 
  "status": "success"
}
~~~
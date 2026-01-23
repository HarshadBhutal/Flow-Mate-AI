from fastapi import FastAPI
from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Optional
from sqlmodel import create_engine,SQLModel,Field,JSON,Column,Session,select
from datetime import datetime,timedelta

engine = create_engine("sqlite:///Schedule.db")


mcp=FastMCP("ToDoAssistant")

class Schedule(SQLModel,table=True):
    User_Id:int = Field(default=None,primary_key=True)
    Task_To_Complete:list[str]=Field(sa_column=Column(JSON))
    remind_at: Optional[datetime] = Field(default=None)

class Tasks(BaseModel):
    task:str
    specific_time:Optional[str]=None
    minutes_from_now:Optional[int]=None

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


create_db_and_tables()


@mcp.tool()
def Create_schedule(tasks: Tasks):
    """
    Creates a new schedule for new user and calculates a reminder timestamp.

    This tool handles both relative time (minutes from now) and specific 
    absolute timestamps. It saves the task to the database and returns 
    a natural language confirmation of the scheduled time.

    Args:
        tasks (Tasks): An object containing the task description, and 
                       optionally 'minutes_from_now' (int) or 
                       'specific_time' (ISO string).

    Returns:
        str: A combined message confirming the creation and the reminder time.
    """

    reminder_time=None

    if tasks.minutes_from_now is not None:
        reminder_time =datetime.now() + timedelta(minutes=tasks.minutes_from_now)

    elif tasks.specific_time:
        try:
            reminder_time = datetime.fromisoformat(tasks.specific_time)
        except ValueError:
            return "Error: specific_time must be in ISO format (YYYY-MM-DD HH:MM:SS)"
   

    with Session(engine) as session:
            todo = Schedule(Task_To_Complete=[tasks.task],remind_at=reminder_time)
            session.add(todo)
            message=f"new to do list created"
            session.commit()
            session.refresh(todo)

    if reminder_time :
    
        if reminder_time.date() == datetime.now().date():
            time_str = reminder_time.strftime("today at %I:%M %p")
        else:
            time_str = reminder_time.strftime("on %B %D at %I:%M %p") 
            
    else:
       time_str = "No reminder set"
    return message,time_str



@mcp.tool()
def add_task(user_id: int, tasks: Tasks):
    """
    Adds a task to an existing schedule and updates the reminder time.

    This tool retrieves an existing schedule by user_id, appends a new task 
    to the list, and updates the reminder timestamp based on either 
    relative minutes or a specific time provided.

    Args:
        user_id (int): The unique database ID of the user's schedule to update.
        tasks (Tasks): An object containing the new 'task' string and optional 
                       timing parameters (minutes_from_now or specific_time).

    Returns:
        str: A natural language confirmation including the updated task 
             list status and the new reminder time.
    """

    reminder_time=None

    if tasks.minutes_from_now is not None:
        reminder_time =datetime.now() + timedelta(minutes=tasks.minutes_from_now)

    elif tasks.specific_time:
        try:
            reminder_time = datetime.fromisoformat(tasks.specific_time)
        except ValueError:
            return "Error: specific_time must be in ISO format (YYYY-MM-DD HH:MM:SS)"
        

    with Session(engine) as session:
        todo = session.get(Schedule, user_id)
        if todo:
            current_tasks = list(todo.Task_To_Complete)
            current_tasks.append(tasks.task)
            todo.Task_To_Complete = current_tasks
            todo.remind_at = reminder_time
            session.add(todo)
            message = f"Task added to the To-Do list"
        else:
            message = "ID not found"
        
        session.commit()
        session.refresh(todo)

    if reminder_time :
    
        if reminder_time.date() == datetime.now().date():
            time_str = reminder_time.strftime("today at %I:%M %p")
        else:
            time_str = reminder_time.strftime("on %B %D at %I:%M %p") 
            
    else:
       time_str = "No reminder set"
    return message,time_str



@mcp.tool()
def get_user_tasks(user_id: int):
    """
    Retrieves all schedule list tasks associated with a specific user ID to check or use with other tools.

    Args:
        user_id (int): The unique identifier of the user whose tasks are being requested.

    Returns:
        list: A list containing  tasks for the specified user.
    """
    with Session(engine) as session:
        statement = select(Schedule).where(Schedule.User_Id == user_id)
        todo = session.exec(statement).first() 
        
        if not todo:
            return {"error": f"No tasks found for user ID {user_id}"}
            
    return {"tasks": todo.Task_To_Complete}



@mcp.tool()
def Task_Done(user_id:int,Task_name:str):
    """
    Delete the task from the schedule list which is completed. 
    
    Args:
         user_id:The unique identifier of the user whose tasks are being requested.
         Task_name:name of the task in the list.

    Returns: 
            str:message if the task is deleted from the tasks list
        
    """
    with Session(engine) as session:
        todo = session.get(Schedule, user_id)
        if todo:
            current_tasks=list(todo.Task_To_Complete)
            current_tasks.remove(Task_name)
            todo.Task_To_Complete=current_tasks
            session.add(todo)
            message="Task is deleted from the list"
        else:
            message="there is not task with the name"
        session.commit()
    return message    


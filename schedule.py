from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Optional
from sqlmodel import create_engine,SQLModel,Field,JSON,Column,Session,select
from datetime import datetime,timedelta

engine = create_engine("sqlite:///Schedule.db")


mcp=FastMCP("ToDoAssistant")

class User(SQLModel,table = True):
    user_id:int = Field(default = None,primary_key = True)
    user_name:str = Field(default=None)
    email:str = Field(unique = True, index = True)
    phone_no:int = Field(unique = True, index = True)

class Schedule(SQLModel,table = True):
    s_id:int = Field(default=None,primary_key = True)
    task_to_complete:list[dict] = Field(default=[],sa_column = Column(JSON))
    user_id:int = Field(foreign_key = "user.user_id")

SQLModel.metadata.create_all(engine)

class Tasks(BaseModel):
    task_name:str
    minutes_from_now:Optional[int]=None
    specific_time:Optional[datetime]=None

@mcp.tool()
def create_user(user: User):

    """
    Registers a new user in the system. 

    This tool creates a profile for the user using their name, email, and 
    phone number. This must be done before the user can add tasks or 
    schedules to the system.

    Args:
        user (User): An object containing the user's details:
            - user_name (str): The person's full name.
            - email (str): A unique email address.
            - phone_no (int): The user's contact number.

    Returns:
        str: A success message confirming the user has been added.
    """

    with Session(engine) as session:
            session.add(user)
            message=f"new user added successfully"
            session.commit()
            session.refresh(user)
    return message


@mcp.tool()
def add_task( email:str, tasks:Tasks, via:str):

    """
    Adds a new task to a user's schedule. 
    
    This tool handles timing through two exclusive options:
    1. Relative time (e.g., "in 5 minutes") 
    2. Absolute time (e.g., "at 5:00 PM")

    Args:
        email (str): The user's registered email.
        tasks (Tasks): Object containing:
            - task_name (str): Description of the task.
            - minutes_from_now (int, optional): Relative offset in minutes.
            - specific_time (datetime, optional): Exact timestamp.
              (Note: Use either minutes_from_now OR specific_time).
        via (str): The preferred reminder method. Must be either 'whatsApp' or 'email'.

    Returns:
        tuple: (status_message, human_readable_time)
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

        statement=select(User).where(User.email==email)
        user=session.exec(statement).first()

        if user:
           todo=session.exec(select(Schedule).where(Schedule.user_id==user.user_id)).first()
        else:
            return "no user" 
        
        if not todo:
            todo = Schedule(user_id=user.user_id, task_to_complete=[])
            session.add(todo)
            session.flush()
        
        task={
            "task_name" : tasks.task_name,
            "remind_at" : reminder_time.isoformat() if reminder_time else None,
            "via" : via
        }

        if todo:
            current_tasks = list(todo.task_to_complete)
            current_tasks.append(task)
            todo.task_to_complete=current_tasks
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
def get_user_tasks(email: str):
    """
    Retrieves the full list of scheduled tasks for a specific user.

    Args:
        email (str): The registered email address of the user.

    Returns:
        dict: A dictionary containing the "tasks" list, or an error message if not found.
    """
    with Session(engine) as session:
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first() 

        if user:
            todo = session.exec(select(Schedule).where(Schedule.user_id == user.user_id)).first()

        else:
            return "user not found"    
        
        if not todo:
            return {"error": f"No tasks found for email ID {email}"}
            
    return {"tasks": todo.task_to_complete}



@mcp.tool()
def Task_Done(email:str, task_name:str):
    """
    Removes a completed task from the user's schedule.

    This tool searches for a task by its name and removes it from the 
    user's persistent storage.

    Args:
        email (str): The registered email address of the user.
        task_name (str): The exact name of the task to be deleted.

    Returns:
        str: A confirmation message indicating if the task was successfully deleted.
    """
    with Session(engine) as session:
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first() 

        if user:
            todo = session.exec(select(Schedule).where(Schedule.user_id == user.user_id)).first()

        else:
            return "user not found"
        
        if todo:
            original_count = len(todo.task_to_complete)
            
            updated_tasks = [t for t in todo.task_to_complete if t.get("task_name") != task_name]

            if len(updated_tasks) < original_count:
                todo.task_to_complete = updated_tasks 
                session.add(todo)
                session.commit()
                return f"Task '{task_name}' has been deleted."
            else:
                return f"No task found with the name '{task_name}'."
        
        return "No schedule found for this user."


from fastapi import FastAPI
from fastmcp import FastMCP
from pydantic import BaseModel
from sqlmodel import create_engine,SQLModel,Field,JSON,Column,Session,select
from contextlib import asynccontextmanager

engine = create_engine("sqlite:///todo.db")

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
    print("closing connection")


app=FastAPI(title="AI Voice Assistant",lifespan=lifespan)

mcp=FastMCP("ToDoAssistant")

class TO_DO(SQLModel,table=True):
    id:int = Field(default=None,primary_key=True)
    Task_To_Complete:list[str]=Field(sa_column=Column(JSON))

class Task(BaseModel):
    item:str


@mcp.tool()
def Create_Todo(task: Task):
    """
    Creates a new task with new user id in the to-do list database.

    Args:
        task (Task): An object containing the 'item' string to be added to the list.
    
    Returns:
        str: A confirmation message indicating the to-do item was successfully created.
    """
    with Session(engine) as session:
            todo = TO_DO(Task_To_Complete=[task.item])
            session.add(todo)
            message=f"new to do list created"
            session.commit()
    return message


@mcp.tool()
def add_task(id: int, task: Task):
    """
    Appends a new task to an existing user's to-do list based on their ID.

    Args:
        id (int): The unique identifier of the user.
        task (Task): The task object containing the item string to add.

    Returns:
        str: A success message if the task is added, or an error message if the ID is not found.
    """
    with Session(engine) as session:
        todo = session.get(TO_DO, id)
        if todo:
            current_tasks = list(todo.Task_To_Complete)
            current_tasks.append(task.item)
            todo.Task_To_Complete = current_tasks
            session.add(todo)
            message = f"Task added to the To-Do list"
        else:
            message = "ID not found"
        
        session.commit()
    return message


@mcp.tool()
def get_user_tasks(user_id: int):
    """
    Retrieves all to-do list tasks associated with a specific user ID.

    Args:
        user_id (int): The unique identifier of the user whose tasks are being requested.

    Returns:
        list: A list containing  tasks for the specified user.
    """
    with Session(engine) as session:
        statement = select(TO_DO).where(TO_DO.id == user_id)
        todo = session.exec(statement).first() 
        
        if not todo:
            return {"error": f"No tasks found for user ID {user_id}"}
            
    return {"tasks": todo.Task_To_Complete}


@app.delete("/task_done/{id}")
def Task_Done(id:int):
    pass
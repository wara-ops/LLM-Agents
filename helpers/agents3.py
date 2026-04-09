import subprocess

def execute_script(script: str) -> str:
    """
    Excecute python code and return the result as a string.
    You may import any python module, e.g. datetime or pandas
    If the script produce a figure, write it to a PNG file in the current working directory

    Args:
        script (str): The python script to evaluate

    Returns:
        str: the result of running the script or an error message in case of failure

    """
    
    script_filename = "temp_script.py"
    work_dir = "work"
    output = ""
    
    with open(f"{work_dir}/{script_filename}", "w") as script_file:
        script_file.write(script)
    try:
        result = subprocess.run(
            ["python", script_filename],
            capture_output=True,
            cwd=work_dir,
            text=True,
            check=True,
        )
        output = result.stdout  
        # Uncomment next line to get debbuging output
        # print("Script output:", output) 
    except subprocess.CalledProcessError:
        output = "Error: Script execution failed"

    return output
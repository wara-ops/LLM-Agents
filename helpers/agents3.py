import subprocess
import os
import re
from IPython.display import Image, display_png
    

def execute_script(script: str) -> str:
    """
    Excecute python code and return the result as a string.
    You may import any python module, e.g. datetime or pandas
    If the script produce a figure, write it to a PNG file in the current working directory and return its name as a string using the format '## Figure: [name] ##' so it is visible to the user,

    Args:
        script (str): The python script to evaluate

    Returns:
        str: the result of running the script or an error message in case of failure

    """
    script_filename = "temp_script.py"
    work_dir = "work"
    output = ""
    
    with open(f"{work_dir}/{script_filename}", "w") as fd:
        fd.write(script)
        
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
    except subprocess.CalledProcessError as e:
        print("Script execution failed:", e.stderr)  

    # Check if a figure was produced and if so, dispaly it
    RE_FIG = re.compile(r'## Figure:\s*(\S+)')
    fig_match = RE_FIG.match(output)
    if fig_match:
        fig_path = f"{work_dir}/{fig_match.group(1)}"
        display_png(Image(filename=fig_path))

    return output

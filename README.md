You create a folder called my-python-project and open it in VS Code.

First, you create a virtual environment:
```
python -m venv .venv
```
This creates a .venv folder inside the project. That folder contains a separate Python environment for this project.

Next, you activate it.

On Windows PowerShell:
```
.venv\Scripts\Activate.ps1
```
If the prompt changes to include (.venv), that is evidence that the environment is active.

Then you upgrade pip:
```
python -m pip install --upgrade pip
```
This matters because pip is the tool that installs Python packages. Using python -m pip is clearer than just typing pip, because it makes sure the package installer belongs to the currently selected Python interpreter.

Example package install

If the project later needs a package such as requests, you would install it like this:
```
python -m pip install pygame
```
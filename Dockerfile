# Use Apify's official Python-Selenium image as the base.
FROM apify/actor-python-selenium:3.12

# Copy only requirements.txt first to leverage Docker cache.
COPY requirements.txt ./

# Install dependencies from requirements.txt.
RUN echo "Python version:" \
    && python --version \
    && echo "Pip version:" \
    && pip --version \
    && echo "Installing dependencies:" \
    && pip install --no-cache-dir -r requirements.txt \
    && echo "All installed packages:" \
    && pip freeze

# Copy the rest of the source code into the container.
COPY . ./

# (Optional) Compile all Python files to check for errors.
RUN python3 -m compileall -q .

# Set the default command to run your main script.
# For example, if your main file is named "main.py", run:
CMD ["python3", "main.py"]

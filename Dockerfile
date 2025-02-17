FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update && apt-get install -y google-chrome-stable

# Debug - what version do we have?
RUN google-chrome --version

# Install matching ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | sed -E 's/.* ([0-9]+)\..*/\1/') \
  && echo "Chrome major version: $CHROME_VERSION" \
  && wget -q "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}" -O /tmp/LATEST_RELEASE \
  && CHROMEDRIVER_VERSION=$(cat /tmp/LATEST_RELEASE) \
  && echo "ChromeDriver version: $CHROMEDRIVER_VERSION" \
  && wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip \
  && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
  && rm /tmp/chromedriver.zip


# Set display (needed for headless Chrome but no real display)
ENV DISPLAY=:99

# Copy requirements if you have any
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy code
COPY . /app
WORKDIR /app

# Run your main.py on container start
ENTRYPOINT ["python", "main.py"]

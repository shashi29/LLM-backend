# LLM-backend

uvicorn app.main:app --reload

reliable-vector-429905-e8

sudo docker build -t gcr.io/reliable-vector-429905-e8/llm-backend .

# Push Docker image to Google Container Registry
sudo docker push gcr.io/reliable-vector-429905-e8/llm-backend


#Steps for installing pyenv 
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
curl https://pyenv.run | bash
echo -e 'export PYENV_ROOT="$HOME/.pyenv"\nexport PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo -e 'eval "$(pyenv init --path)"\neval "$(pyenv init -)"' >> ~/.bashrc
exec "$SHELL"
pyenv --version

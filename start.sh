# Arranca e reconstrói todos os serviços; ignora erros
docker-compose up -d --build --scale node1=3 --scale gateway=2 --scale worker=3

echo "Containers iniciados"

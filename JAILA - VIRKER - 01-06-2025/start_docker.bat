@echo off
echo Starter JAILA Docker-containere...
echo.

cd %~dp0docker
echo Navigeret til Docker-mappen: %cd%
echo.

echo Starter containere med docker-compose...
docker-compose up -d

echo.
echo Containere er startet! Du kan nu bruge JAILA.
echo Weaviate burde være tilgængelig på http://localhost:8080
echo.

echo Viser kørende containere:
docker ps

echo.
echo Tryk på en tast for at lukke dette vindue...
pause > nul

@echo off

call C:\OSGeo4W64\bin\o4w_env.bat
call C:\OSGeo4W64\bin\py3_env.bat

set makepath=%~dp0
call %makepath%\make.bat html

timeout /t 3

#!/bin/bash
cd /Users/marciocarneiro/Documents/1\ projetos/python/planilhas
export $(cat .env | xargs)
pipenv shell
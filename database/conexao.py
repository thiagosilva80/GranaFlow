import sqlite3

def criar_conexao():
    conexao = sqlite3.connect("granaflow.db")
    conexao.row_factory = sqlite3.Row
    
    return conexao
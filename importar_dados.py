# CUIDADO: Isso apaga todos os registros marcados como Regional 1
def limpar_regional_1():
    docs = db.collection("participantes").where("unidade", "==", "Regional 1").stream()
    for doc in docs:
        doc.reference.delete()
    print("🗑️ Regional 1 limpa com sucesso!")

# limpar_regional_1() # Descomente para usar
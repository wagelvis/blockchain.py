from hashlib import sha256
import json
import time

from flask import Flask, request
import requests


class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        # Una función que devuelve el hash del contenido del bloque.
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class Blockchain:
    # Dificultad de nuestro algoritmo PoW
    difficulty = 2

    def __init__(self):
        self.unconfirmed_transactions = []
        self.chain = []
        # self.create_genesis_block()

    def create_genesis_block(self):
        # Una función para generar el bloque de la génesis y añadirlo a la cadena.
        # El bloque tiene el índice 0, previous_hash como 0, y un hash válido.
        genesis_block = Block(0, [], 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        # Una función que añade el bloque a la cadena después de la verificación.
        # La verificación incluye:
        # * Comprobar si la prueba es válida.
        # * El previous_hash referido en el bloque y el hash del último bloque de la cadena coinciden.
        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            return False

        if not self.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @staticmethod
    def proof_of_work(block):
        # Función que intenta diferentes valores de nonce para obtener un hash que satisfaga nuestro criterio de dificultad.
        block.nonce = 0

        computed_hash = block.compute_hash()

        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        # Comprueba si block_hash es un hash válido de bloque y satisface el criterio de dificultad.
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            # Eliminar el campo de hash para volver a calcular el hash de nuevo
            # usando el método `compute_hash`.
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block.hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):
        # Esta función sirve como interfaz para añadir las transacciones pendientes a la cadena de bloques añadiéndolas al bloque y averiguando la prueba de trabajo.
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_transactions = []

        return True


app = Flask(__name__)

# La copia de blockchain del nodo
blockchain = Blockchain()
blockchain.create_genesis_block()

# La dirección de otros miembros participantes de la red
peers = set()


# Endpoint para presentar una nueva transacción. 
# Esto será usado por nuestra aplicación para añadir nuevos datos (posts) a la cadena de bloques.
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["author", "content"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Datos de transacción no válidos", 404

    tx_data["timestamp"] = time.time()

    blockchain.add_new_transaction(tx_data)

    return "Operación Exitosa", 201


# Endpoint para devolver la copia del nodo de la cadena.
# Nuestra aplicación usará este endpoint para consultar todos los mensajes a mostrar.
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       "peers": list(peers)})


# Endpoint para solicitar al nodo que extraiga las transacciones no confirmadas (si las hay).
# Lo usaremos para iniciar un comando de minado desde nuestra aplicación.
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No hay transacciones a Minar"
    else:
        # Asegurarse de que tenemos la cadena más larga antes de anunciar a la red
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            # Anunciar el bloque recientemente minado a la red
            announce_new_block(blockchain.last_block)
        return "El Bloque #{} ha sido minado.".format(blockchain.last_block.index)


# Endpoint para agregar un bloque minado por alguien más a la cadena del nodo.
# El bloque es verificado primero por el nodo y luego se agrega a la cadena.
@app.route('/add_block', methods=['POST'])
def validate_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp",
                             block_data["previous_hash"]])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "El bloque fue descartado por el nodo", 400

    return "Bloque añadido a la cadena", 201


# Endpoint para agregar nuevo par a la red.
@app.route('/register_node', methods=['POST'])
def register_new_peers():
    nodes_address = request.get_json()["node_address"]
    if not nodes_address:
        return "Datos no válidos", 400

    # Agregar el nodo a la lista de pares
    peers.add(node)

    # Devuelve la cadena de bloqueo consensuada al nodo recién registrado
    # para que pueda sincronizarse
    return get_chain()


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    # Internamente llama al endpoint `register_node` para registrar el nodo actual con el nodo especificado en la petición,
    # y sincronizar la cadena de bloques así como los datos de los pares.
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Datos no válidos", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Realizar una solicitud para registrarse en el nodo remoto y obtener información
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global peers
        # Actualización de la cadena y de los pares
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registro exitoso", 200
    else:
        # Si algo sale mal, se pasa a la respuesta de la API
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # Omitir el bloque génesis
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("La cadena de descarga ha sido manipulada!!")
    return generated_blockchain


# Endpoint para añadir un bloque minado por otra persona a la cadena del nodo.
# El bloque se verifica primero por el nodo y luego se agrega a la cadena.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "El bloque fue descartado por el nodo", 400

    return "Bloque agregado a la cadena", 201


# Endpoint para consultar las transacciones no confirmadas.
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


def consensus():
    # Nuestro simple algoritmo de conseso.
    # Si una cadena de validez más larga es encontrada, nuestra cadena se reemplaza con él.
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('http://{}/chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


def announce_new_block(block):
    # Una función para anunciar a la red una vez que un bloque ha sido minado.
    # Otros bloques pueden simplemente verificar la prueba de trabajo y añadirla a su respectivas cadenas.
    for peer in peers:
        url = "http://{}/add_block".format(peer)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True))


app.run(debug=True, port=8000)

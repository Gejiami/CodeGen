import json

import faiss
from langchain_community.docstore import InMemoryDocstore
from langchain_community.vectorstores import FAISS
import os


current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)

VS_DIR = os.path.dirname(current_dir)
VECTORSTORE = os.path.join(VS_DIR, 'vectorstore')

class VectorStore:
    def __init__(self, embeddings_model, project_name, sha, update_from_sha=None):
        self.db = None
        self.embeddings_model = embeddings_model
        self.create_dir()
        self.project_name = project_name
        self.sha = sha
        self.update_from_sha = update_from_sha

    def create_dir(self):
        if not os.path.exists(VECTORSTORE):
            # create if dir does not exist
            os.makedirs(VECTORSTORE)
            print('Vector Database directory created successfully')

    def read_index(self):
        if os.path.exists(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.json')):
            with open(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.json'), 'r') as f:
                index_dict = json.load(f)
        elif self.update_from_sha \
                and os.path.exists(os.path.join(VECTORSTORE, f'{self.project_name}_{self.update_from_sha}.json')):
            with open(os.path.join(VECTORSTORE, f'{self.project_name}_{self.update_from_sha}.json'), 'r') as f:
                index_dict = json.load(f)
        else:
            index_dict = {}
        return index_dict

    def write_index(self, index_dict):
        with open(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.json'), 'w') as f:
            json.dump(index_dict, f)

    def add_documents(self, docs):
        # read last index in file
        index_dict = self.read_index()
        # create ids by file names in metadata
        ids = []
        for doc in docs:
            file_name = doc.metadata['file_name']
            last_index = index_dict.get(file_name, -1)
            doc_id = file_name + '-' + str(last_index + 1)
            index_dict[file_name] = last_index + 1
            ids.append(doc_id)
        self.db.add_documents(documents=docs, ids=ids)
        # record last index
        self.write_index(index_dict)

    def remove_documents(self, file_names):
        index_dict = self.read_index()
        for file_name in file_names:
            last_index = index_dict.get(file_name, -1)
            if last_index != -1:
                result = self.db.delete([file_name + '-' + str(idx) for idx in range(last_index+1)])
                if result:
                    # print(f"File {file_name} documents removed successfully")
                    index_dict.pop(file_name)
                else:
                    print(f"File {file_name} documents fail to be removed")
        self.write_index(index_dict)

    def match_documents(self, instruction):
        retriever = self.db.as_retriever()
        matched_docs = retriever.invoke(instruction)
        return matched_docs

    def load_db(self):
        if os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.faiss')) \
                and os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.pkl')) \
                and os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.json')):
            self.db = FAISS.load_local(VECTORSTORE, self.embeddings_model, f"{self.project_name}_{self.sha}",
                                       allow_dangerous_deserialization=True)
            print("Vector database loaded successfully.")
            return 1
        elif os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.update_from_sha}.faiss')) \
                and os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.update_from_sha}.pkl')) \
                and os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.update_from_sha}.json')):
            self.db = FAISS.load_local(VECTORSTORE, self.embeddings_model,
                                       f"{self.project_name}_{self.update_from_sha}",
                                       allow_dangerous_deserialization=True)
            print("Vector database from another commit loaded successfully.")
            return 2
        else:
            self.db = FAISS(
                embedding_function=self.embeddings_model,
                index=faiss.IndexFlatIP(len(self.embeddings_model.embed_query("faiss"))),
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )
            print("No current vector database found, new one created.")
            return 0

    def load_refreshed_db(self):
        if os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.faiss')):
            os.remove(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.faiss'))
        if os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.pkl')):
            os.remove(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.pkl'))
        if os.path.isfile(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.json')):
            os.remove(os.path.join(VECTORSTORE, f'{self.project_name}_{self.sha}.json'))
        self.db = FAISS(
                embedding_function=self.embeddings_model,
                index=faiss.IndexFlatIP(len(self.embeddings_model.embed_query("faiss"))),
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )
        print("Vector store refreshed and created successfully.")

    def save_db(self):
        self.db.save_local(VECTORSTORE, f"{self.project_name}_{self.sha}")
        print("Vector database saved successfully")
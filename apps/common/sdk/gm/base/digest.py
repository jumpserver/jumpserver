from .const import HASH_ALG_ID


class Digest:

    def __init__(self, session, alg_name="sm3"):
        if HASH_ALG_ID.get(alg_name) is None:
            raise Exception("unsupported hash alg {}".format(alg_name))

        self._alg_name = alg_name
        self._session = session
        self.__init_hash()

    def __init_hash(self):
        self._session.hash_init(HASH_ALG_ID[self._alg_name])

    def update(self, data):
        self._session.hash_update(data)

    def final(self):
        return self._session.hash_final()

    def reset(self):
        self.__init_hash()

    def destroy(self):
        self._session.close()
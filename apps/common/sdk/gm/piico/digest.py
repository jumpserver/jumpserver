hash_alg_id = {
    "sm3": 0x00000001,
    "sha1": 0x00000002,
    "sha256": 0x00000004,
    "sha512": 0x00000008,
}


class Digest:

    def __init__(self, session, alg_name="sm3"):
        if hash_alg_id[alg_name] is None:
            raise Exception("unsupported hash alg {}".format(alg_name))

        self._alg_name = alg_name
        self._session = session
        self.__init_hash()

    def __init_hash(self):
        self._session.hash_init(hash_alg_id[self._alg_name])

    def update(self, data):
        self._session.hash_update(data)

    def final(self):
        return self._session.hash_final()

    def reset(self):
        self.__init_hash()

    def destroy(self):
        self._session.close()

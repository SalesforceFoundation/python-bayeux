from getpass import getpass
from pytest import fixture
from python_bayeux import BayeuxClient

import gevent
import simplejson as json
import random
from string import ascii_letters


class ClientOne(BayeuxClient):
    def test_shutdown(self, connect_response_element):
        self.value = connect_response_element
        self.publish(
            'Ok, I got {0}. Checking if it is right...'.format(
                self.value['data']['chat']
            ),
            'TestUser'
        )
        self.shutdown()

    def publish(self, message, username):
        super(ClientOne, self).publish(
            '/chat/demo',
            {
                'chat': message,
                'user': username
            }
        )


class ClientTwo(BayeuxClient):
    def test_print_some_stuff(self, connect_response_element):
        if not hasattr(self, 'counter'):
            self.counter = 0

        if not hasattr(self, 'detected_randoms'):
            self.detected_randoms = set([])
        try:
            self.detected_randoms.add(json.loads(
                connect_response_element['data']['chat']
            )['generated_random'])
        except json.JSONDecodeError:  # Ignore non-JSON chats
            return

        self.counter += 1
        if self.counter == 5:
            self.shutdown()

    def start_publish_loop(self):
        loop_greenlet = gevent.Greenlet(self._publish_loop)
        self.greenlets.append(loop_greenlet)
        loop_greenlet.start()

    def _publish_loop(self):
        while not self.stop_greenlets:
            self.publish(
                'I am a test looping.',
                'TestUserLooping'
            )
            gevent.sleep(1)

    def publish(self, message, username):
        if not hasattr(self, 'generated_randoms'):
            self.generated_randoms = set([])

        generated_random = random.random()

        super(ClientTwo, self).publish(
            '/chat/demo',
            {
                'chat': json.dumps({
                    'message': message,
                    'generated_random': generated_random,
                    'sending_client_id': self.client_id
                }),
                'user': username
            }
        )
        self.generated_randoms.add(generated_random)


@fixture(scope='module')
def please_start_demo():
    getpass(
        '\nPlease start the cometd-demo and hit enter when ready. '
        'This is often done by going to the cometd-demo/ directory '
        'in the cometd distribution and running \n'
        '$ mvn jetty:run\n'
    )


def test_one_client(please_start_demo):
    # Using getpass() only because I know it handles the py.test tty redirect
    # well
    code = ''.join(random.choice(ascii_letters) for i in range(12))
    getpass(
        'Point a browser to \n'
        'http://localhost:8080/jquery-examples/chat/\n'
        'Enter a chat name, and click the Join button.\n'
        'Watch for the chat prompt.  When prompted, '
        'copy the following string into then chat'
        ' : {0}\n'
        'Hit enter when you are ready:'.format(
            code
        )
    )
    with ClientOne('http://localhost:8080/cometd') as client:
        client.subscribe('/chat/demo', 'test_shutdown')
        client.publish(
            'Please enter the test code!',
            'TestUser'
        )
        try:
            client.block()
        except KeyboardInterrupt:
            assert False
        assert client.value['data']['chat'] == code


def test_two_clients(please_start_demo):
    with ClientTwo('http://localhost:8080/cometd') as client1:
        client1.go()

        with ClientTwo('http://localhost:8080/cometd') as client2:
            client2.subscribe('/chat/demo', 'test_print_some_stuff')

            client2.publish(
                'I am a test 2.',
                'TestUser2'
            )

            client1.start_publish_loop()
            try:
                client2.block()
            except KeyboardInterrupt:
                assert False
            for element in client2.detected_randoms:
                assert element in client1.generated_randoms

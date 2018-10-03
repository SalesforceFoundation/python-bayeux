'''
    Copyright (c) 2016, Salesforce.org
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Salesforce.org nor the names of
      its contributors may be used to endorse or promote products derived
      from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
    FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
    INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
    BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
    CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
    LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
    ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
'''

from getpass import getpass
from pytest import fixture
from pytest import raises
from python_bayeux import BayeuxClient
from python_bayeux import RepeatedTimeoutException
from types import MethodType

import gevent
import simplejson as json
import random
from string import ascii_letters
import requests


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


def test_one_client_go_then_block(please_start_demo):
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
        client.go()
        try:
            client.block()
        except KeyboardInterrupt:
            assert False
        assert client.value['data']['chat'] == code


def test_one_client_subscribe_timeouts(please_start_demo, monkeypatch):
    # Using getpass() only because I know it handles the py.test tty redirect
    # well
    getpass(
        'Point a browser to \n'
        'http://localhost:8080/jquery-examples/chat/\n'
        'Enter a chat name, and click the Join button.\n'
        'Hit enter when you are ready:'
    )

    def patched_send_message(self, payload, **kwargs):
        if 'channel' in payload and payload['channel'] == '/meta/subscribe':
            raise requests.exceptions.ReadTimeout()
        else:
            return self._real_send_message(payload, **kwargs)

    with ClientOne('http://localhost:8080/cometd') as client:
        client._real_send_message = client._send_message
        client._send_message = MethodType(patched_send_message, client)

        client.subscribe('/chat/demo', 'test_shutdown')
        client.publish(
            'No need to enter a test code.  Just wait...',
            'TestUser'
        )
        try:
            client.block()
        except KeyboardInterrupt:
            assert False

        # This depends on the order that outbound_greenlets is populated
        assert isinstance(
            client.outbound_greenlets[0].exception,
            RepeatedTimeoutException
        )
        assert not hasattr(client, 'value')


def test_one_client_unsubscribe_timeouts(please_start_demo, monkeypatch):
    # Using getpass() only because I know it handles the py.test tty redirect
    # well
    getpass(
        'Point a browser to \n'
        'http://localhost:8080/jquery-examples/chat/\n'
        'Enter a chat name, and click the Join button.\n'
        'Hit enter when you are ready:'
    )

    def patched_send_message(self, payload, **kwargs):
        if 'channel' in payload and payload['channel'] == '/meta/unsubscribe':
            raise requests.exceptions.ReadTimeout()
        else:
            return self._real_send_message(payload, **kwargs)

    with ClientOne('http://localhost:8080/cometd') as client:
        client._real_send_message = client._send_message
        client._send_message = MethodType(patched_send_message, client)

        client.subscribe('/chat/demo', 'test_shutdown')
        client.publish(
            'No need to enter a test code.  Just wait...',
            'TestUser'
        )
        client.unsubscribe('/chat/demo')
        try:
            client.block()
        except KeyboardInterrupt:
            assert False

        # This depends on the order that outbound_greenlets is populated
        assert isinstance(
            client.outbound_greenlets[1].exception,
            RepeatedTimeoutException
        )
        assert not hasattr(client, 'value')


def test_one_client_subscribe_timeouts_recover(please_start_demo, monkeypatch):
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

    def patched_send_message(self, payload, **kwargs):
        if 'channel' in payload and payload['channel'] == '/meta/subscribe':
            self.test_num_timeouts = 0  \
                if not hasattr(self, 'test_num_timeouts') \
                else self.test_num_timeouts + 1

            if self.test_num_timeouts > 5:
                return self._real_send_message(payload, **kwargs)

            raise requests.exceptions.ReadTimeout()
        else:
            return self._real_send_message(payload, **kwargs)

    with ClientOne('http://localhost:8080/cometd') as client:
        client._real_send_message = client._send_message
        client._send_message = MethodType(patched_send_message, client)

        client.subscribe('/chat/demo', 'test_shutdown')
        client.publish(
            'In about 30 seconds, please enter the test code!',
            'TestUser'
        )
        try:
            client.block()
        except KeyboardInterrupt:
            assert False
        assert client.value['data']['chat'] == code


def test_one_client_unsubscribe_timeouts_recover(please_start_demo,
                                                 monkeypatch):
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

    def patched_send_message(self, payload, **kwargs):
        if 'channel' in payload and payload['channel'] == '/meta/unsubscribe':
            self.test_num_timeouts = 0  \
                if not hasattr(self, 'test_num_timeouts') \
                else self.test_num_timeouts + 1

            if self.test_num_timeouts > 5:
                return self._real_send_message(payload, **kwargs)

            raise requests.exceptions.ReadTimeout()
        else:
            return self._real_send_message(payload, **kwargs)

    with ClientOne('http://localhost:8080/cometd') as client:
        client._real_send_message = client._send_message
        client._send_message = MethodType(patched_send_message, client)

        client.subscribe('/chat/demo', 'test_shutdown')
        client.publish(
            'Please wait...',
            'TestUser'
        )
        client.unsubscribe('/chat/demo')
        client.publish(
            'Please keep waiting...',
            'TestUser'
        )
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


class BrokenClient(BayeuxClient):
    def test_exception(self, connect_response_element):
        raise Exception('ouch')

    def publish(self, message, username):
        super(BrokenClient, self).publish(
            '/chat/demo',
            {
                'chat': message,
                'user': username
            }
        )


def test_broken_client(please_start_demo):
    # Using getpass() only because I know it handles the py.test tty redirect
    # well
    getpass(
        'Point a browser to \n'
        'http://localhost:8080/jquery-examples/chat/\n'
        'Enter a chat name, and click the Join button.\n'
        'Hit enter when you are ready:'
    )

    with BrokenClient('http://localhost:8080/cometd') as client:
        client.subscribe('/chat/demo', 'test_exception')

        client.publish(
            'Please enter any chat message.',
            'TestUser'
        )

        client.go()
        try:
            client.block()
        except KeyboardInterrupt:
            assert False

        # This depends on the order that client.greenlets is populated
        assert isinstance(
            client.greenlets[-1].exception,
            Exception
        )

        assert str(client.greenlets[-1].exception) == 'ouch'


def test_broken_client_same_greenlet(please_start_demo):
    # Using getpass() only because I know it handles the py.test tty redirect
    # well
    getpass(
        'Point a browser to \n'
        'http://localhost:8080/jquery-examples/chat/\n'
        'Enter a chat name, and click the Join button.\n'
        'Hit enter when you are ready:'
    )

    with BrokenClient('http://localhost:8080/cometd') as client:
        client.subscribe('/chat/demo', 'test_exception')

        client.publish(
            'Please enter any chat message.',
            'TestUser'
        )

        with raises(Exception) as e:
            client.block()
            assert str(e) == 'ouch'


def test_broken_client_local_loop(please_start_demo):
    # Using getpass() only because I know it handles the py.test tty redirect
    # well
    getpass(
        'Point a browser to \n'
        'http://localhost:8080/jquery-examples/chat/\n'
        'Enter a chat name, and click the Join button.\n'
        'Hit enter when you are ready:'
    )

    with BrokenClient('http://localhost:8080/cometd') as client:
        client.subscribe('/chat/demo', 'test_exception')

        client.publish(
            'Please enter any chat message.',
            'TestUser'
        )

        client.go()
        try:
            while not client.disconnect_complete:
                gevent.sleep(0.5)
        except KeyboardInterrupt:
            assert False

        # This depends on the order that client.greenlets is populated
        assert isinstance(
            client.greenlets[-1].exception,
            Exception
        )

        assert str(client.greenlets[-1].exception) == 'ouch'

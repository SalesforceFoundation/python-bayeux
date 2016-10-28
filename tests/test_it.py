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

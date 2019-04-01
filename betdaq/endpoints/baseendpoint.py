
import datetime

import xmltodict
from requests import ConnectionError
from zeep.helpers import serialize_object

from betdaq.exceptions import APIError
from betdaq.utils import check_status_code, make_tz_naive


class BaseEndpoint(object):

    def __init__(self, parent):
        """
        :param parent: API client.
        """
        self.client = parent

    def request(self, method, params, secure=False, raw=False):
        """
        :param method: The endpoint to be requested.
        :param params: Params to be used in request.
        :param secure: Whether the method belongs to the secure or readonly service.
        :param raw: Whether or not we want to return the raw response
        """
        try:
            if secure:
                response = self.client.secure_client.service[method](params)
            else:
                _method = self.client.readonly_client.service[method]
                if raw:
                    _method._proxy._client.raw_response=True

                try:
                    response = _method(params)
                finally:
                    if raw:
                        _method._proxy._client.raw_response = False

                if raw:
                    result = xmltodict.parse(response.content)
                    return result['soap:Envelope']['soap:Body']

        except ConnectionError:
            raise APIError(None, method, params, 'ConnectionError')
        except Exception as e:
            raise APIError(None, method, params, e)
        data = serialize_object(response)
        check_status_code(data)
        return data

    @staticmethod
    def process_response(response, date_time_sent, result_target, error_handler=None):
        """
        :param response: Response from request
        :param date_time_sent: Date time sent
        :param error_handler: function to parse _raw_elements from zeep response.
        :param result_target: name of the key to get response data from, changes per endpoint.
        """
        date_time_received = make_tz_naive(response.get('Timestamp')) or datetime.datetime.utcnow()
        if error_handler and response.get('_raw_elements'):
            response = error_handler(response)
        return {
            'data': response.get(result_target, []) if result_target else response,
            'date_time_sent': date_time_sent,
            'date_time_received': date_time_received,
        }


def elem2dict(node):
    """
    Convert an lxml.etree node tree into a dict.
    """
    result = {}

    for element in node.iterchildren():
        # Remove namespace prefix
        key = element.tag.split('}')[1] if '}' in element.tag else element.tag

        # Process element as tree element if the inner XML contains non-whitespace content
        if element.text and element.text.strip():
            value = element.text
        else:
            value = elem2dict(element)

        print('setting key %s' % key)
        if key in result:
            result[key] = [result[key], value]
        else:

            result[key] = value

    return result
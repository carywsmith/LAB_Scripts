import sys
import socket
try:
    from json import loads
except ImportError:
    from simplejson import loads

# Python version compatibility:
try:
    # for 3-series Python:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen, URLError
except ImportError:
    # for 2-series Python:
    from urllib import urlencode
    from urllib2 import Request, urlopen, URLError
except:
    sys.stderr.write("Failed to import modules(s) for URL encoding!!\n")
    sys.exit(1)

#socket.setdefaulttimeout(4) # seconds
socket.setdefaulttimeout(180) # seconds

class Superfin(object):
    POST = 'POST'
    GET = 'GET'

    def __init__(self, address, slash=True, debug=False):
        self.address = address
        self._add_slash = slash
        self._debuggage = debug

    def list_param_to_args(self, param, required_args):
        # Check if the parameter is a list
        if not isinstance(param, list):
            # Make it a list
            param = [param]
        
        # Check each list member is a dict
        for i, item in enumerate(param):
            if isinstance(item, dict):
                # Check it has the right members
                if not all (k in item for k in (required_args)):
                    raise Exception('Parameter %d must contain %s' % (i, ','.join(required_args)))
            else:
                raise Exception('Parameter %d must be a dictionary' % (i))
        
        # Set up a list of empty dicts for all the required arguments so .append() works
        args = dict((arg,[]) for arg in required_args)
        for item in param:
            for arg in required_args:
                args[arg].append(item[arg])

        return args
        
    def request(self, req_type, name, args={}):
        # Build XHR URL
        url = 'http://' + self.address + '/cgi-bin/' + name;
        if self._add_slash:
            if self._debuggage:
                sys.stderr.write("added a trailing slash!\n")
            url += '/'

        # Include 'out' parameter to make handling the request building easier
        args['out'] = 'json'
        for key in args:
            type(args[key])
            # Turn arg array into comma-delimited lists
            if type(args[key]) is list:
                args[key] = ','.join(str(x) for x in args[key])

        data = urlencode(args)

        if self.POST == req_type:
            req = Request(url, data)
            if self._debuggage:
                sys.stderr.write("POSTing!\n")
        else:
            req = Request(url + '?' + data)

        if self._debuggage:
            sys.stderr.write("url:  %s\n" % url)
            sys.stderr.write("data: %s\n" % data)
            sys.stderr.write("\n")
        req.get_method = lambda: req_type
        try:
            response = urlopen(req)
        except URLError as e:
            if hasattr(e, 'reason'):
                error = 'We failed to reach a server. Reason: ' + str(e.reason)
            elif hasattr(e, 'code'):
                error = 'The server could not fulfill the request. Error code: ' + str(e.code)
            return {'error': error}
        except socket.timeout as e:
            return {'error': 'Warning: socket timeout'}
        else:
            try:
                json = response.read().decode('utf-8')
                try:
                    response = loads(json)
                except ValueError as e:
                    return {'error': 'Error: ' + str(e), 'json': json}
                else:
                    return response
            except socket.timeout:
                return {'error': 'Warning: socket timeout'}


    def axis_fault(self, axis=0):
        args = {};
        args['axis'] = axis
        return self.request(self.POST, 'axis_fault', args)

    def axis_reset(self, axis=0):
        args = {}
        args['axis'] = axis
        return self.request(self.POST, 'axis_reset', args)

    def get_calibration(self):
        return self.request(self.GET, 'calibration')

    def set_calibration(self, param):
        required_args = ['id', 'desc', 'units', 'filter', 'c0', 'c1', 'c2', 'c3']

        args = self.list_param_to_args(param, required_args)
        
        return self.request(self.POST, 'calibration', args)

    def config_motor_axis(self, axis, port, current_run, current_hold, current_delay, vel, accel, jerk):
        args = {}
        args['axis'] = axis
        args['port'] = port
        args['current-run'] = current_run
        args['current-hold'] = current_hold
        args['current-delay'] = current_delay
        args['vel'] = vel
        args['accel'] = accel
        args['jerk'] = jerk
        return self.request(self.POST, 'config_motor_axis', args)

    def cooler(self, id, enable, level):
        args = {}
        args['cooler_id'] = id
        args['cooler_enable'] = enable
        args['cooler_level'] = level
        return self.request(self.POST, 'cooler', args)

    def get_eeprom(self, slot=0):
        args = {}
        args['slot'] = slot;
        return self.request(self.GET, 'eeprom', args)

    def set_eeprom(self, filename, slot=0):
        raise Exception('Write EEPROM not implemented for Python wrapper')
        #
        # TODO: return self.request(self.POST, 'eeprom', args)
        #

    def enable(self, id, enable):
        args = {}
        args['id'] = id
        args['enable'] = enable
        return self.request(self.POST, 'enable', args)

    def expose(self, id, time):
        args = {}
        args['id'] = id
        args['time'] = time
        return self.request(self.POST, 'expose', args)

    def focus(self, axis=0, magnitude=0, type='relative'):
        args = {}
        args['axis'] = axis
        args['magnitude'] = magnitude
        args['type'] = type
        return self.request(self.POST, 'focus', args)

    def home(self, axis=0):
        args = {}
        args['axis'] = axis
        return self.request(self.POST, 'home', args)

    def get_limits(self,):
        return self.request(self.GET, 'limits')

    def set_limits(self, positive, negative, tilt ):
        args = {}
        args['sw-limit-positive'] = positive
        args['sw-limit-negative'] = negative
        args['sw-limit-tilt'] = tilt
        return self.request(self.POST, 'limits', args)

    def move_axis_linear(self, axis=0, distance=0, type='relative'):
        args = {}
        args['axis'] = axis
        args['distance'] = distance
        args['type'] = type
        return self.request(self.POST, 'move_axis_linear', args)

    def move_axis_rotary(self, axis=0, angle=0, type='relative'):
        args = {}
        args['axis'] = axis
        args['angle'] = angle
        args['type'] = type
        return self.request(self.POST, 'move_axis_rotary', args)

    def pmd(self):
        return self.request(self.GET, 'pmd')

    def pmd_reset(self):
        return self.request(self.POST, 'pmd_reset')

    def position(self, param):
        required_args = ['axis', 'position']

        args = self.list_param_to_args(param, required_args)

        return self.request(self.POST, 'position', args)

    def pressure(self, id, value):
        args = {}
        args['id'] = id
        args['value'] = value
        return self.request(self.POST, 'pressure', args )

    def reboot(self):
        # Call to this method probably won't return in a reasonable time
        args = {}
        args['reboot'] = 'reboot'
        return self.request(self.POST, 'reboot', args )

    def selftest(self, level):
        args = {}
        args['level'] = level
        return self.request(self.POST, 'selftest', args )

    def set_mechanical_zero(self):
        return self.request(self.POST, 'set_mechanical_zero')

    def status(self):
        return self.request(self.GET, 'status')

    def stop(self):
        return self.request(self.POST, 'stop')

    def tilt(self, direction, size):
        args = {}
        args['direction'] = direction;
        args['size'] = size;
        return self.request(self.POST, 'tilt', args)

    def upgrade(self, version):
        args = {}
        args['version'] = version
        return self.request(self.POST, 'upgrade', args)

    def program_fpga(self, version):
        args = {}
        args['version'] = version
        return self.request(self.POST, 'program_fpga', args)


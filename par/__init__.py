from badger import environment
from pvaccess import *
import pvapy as pva
import numpy as np

from time import sleep


class Environment(environment.Environment):

    name = 'par'  # name of the environment
    variables = {  # variables and their hard-limited ranges
        'L4:TM:sledTrigAO': [-0.2, -0.68],
        'LTP:H3:CurrentAO': [-2.0, 2.0],
        'LTP:H2:CurrentAO': [-2.0, 2.0],
        'LTP:H1:CurrentAO': [-2.0, 2.0],
        'LTP:V3:CurrentAO': [-2.0, 2.0],
        'LTP:V2:CurrentAO': [-2.0, 2.0],
        'LTP:V1:CurrentAO': [-2.0, 2.0],
    }
    observables = ['PAR:awg:rms:B:region8' ]  # measurements
    # test values before reading

    _test_variables = {'L2:P1:BPM.VAL' : [0.005,2.0],
            'PAR:RF12:gapVoltage1': [2.0,30.0],
            'L2:P3:BPM.VAL': [0.0050000000000000001,2.0],
            'L2:P4:BPM.VAL': [0.0050000000000000001,2.0],
            'LTP:PH1:BPM.VAL': [5.5,100.0],
            'LTP:FCM:qTotalAI':[0.5,22.0],
            'It:ParIKickerChargeStatCC.SEVR':[-0.5,0.5],
            'It:Par:PSPchargeLimitTimOBO.VAL':[-0.5,0.5],
            'It:ParInjChargeStatCC.SEVR':[-0.5,0.5],
            'It:ParExtChargeStatCC.SEVR':[-0.5,0.5],
            'It:Ddg2chan4.GATE':[0.5,1.5],
            'It:ER1:er.OTL2':[0.5,1.5],
            'It:ParInjChargeDDG.GATE':[0.5,1.5],
            'It:ParExtChargeDDG.GATE':[0.5,1.5],
            'LTP:ControlLawXRC.RUN':[-0.5,0.5]
            }
    def get_variables(self,variable_names):
        """
        input is a list
        get pvs but first check if the conditons are met

        """
        #if self.test_conditions(self._test_variables):
        #    pass
        
        channels = pva.MultiChannel(variable_names, pva.CA)
        get_value = [v[0]['value'] for v in channels.get().toDict()['value']]


        return {variable_names[k]: get_value[k] for k in range(len(variable_names))}


    def set_variables(self,variable_inputs: dict[str, float]):
        """
        Set PVs and verify their values.

        Parameters:
            variable_inputs (dict[str, float]): A dictionary mapping PV names to values.

        Raises:
            Exception: If the values could not be set after retries.
        """
        
        TEST_RUN = False
        if TEST_RUN:
            print (len(variable_inputs.keys()))
            return 
        else:
            pass

        channels = pva.MultiChannel(list(variable_inputs.keys()), pva.CA)
        values = list(variable_inputs.values())

        #channels.putAsDoubleArray(list(variable_inputs.values()))
        verify = False

        """try to verify variables  """
        for i in range(3):
            print(f'verifying {i}')
            sleep(0.1)
            new_values = [v[0]['value'] for v in channels.get().toDict()['value']]
            verify = np.isclose(new_values,values,atol=1e-3).all()
            if verify:
                break
            else:
                pass
        if verify:
            print ('setting variables done')
            #return new_values
        else:
            print (new_values,variable_inputs.values())
            raise Exception("could not write values, check pvs")

    def get_observables(self,observable_names):
        """
        Retrieve observable values.

        Parameters:
            observable_names (list[str]): A list of observable PV names.
            _test_variables (dict): A dictionary mapping PV names to (min_val, max_val) tuples.

        Returns:
            dict[str, float]: A dictionary mapping observable names to their averaged values over time.
        """
        max_attempts = 10
        required_successful_readings = 5
        sleep_time = 0.5
        observed_values_list = []

        # Initialize channels for observables outside the loop
        channels = pva.MultiChannel(observable_names, pva.CA)

        for attempt in range(max_attempts):
            conditions = True
            # Check test conditions
            for key, (min_val, max_val) in _test_variables.items():
                current_value = pva.Channel(key, pva.CA).get()['value']
                if isinstance(current_value, dict):
                    current_value = current_value['index']
                if not min_val <= current_value <= max_val:
                    print(f'Condition not met for {key}: Expected between {min_val} and {max_val}, got {current_value}')
                    conditions = False
                    break  # Exit the condition check loop if a condition fails
            if conditions:
                # Retrieve observable values
                raw_values = channels.get().toDict()['value']
                observed_values = [v[0]['value'] for v in raw_values]
                observed_values_list.append(observed_values)
                if len(observed_values_list) >= required_successful_readings:
                    # Required number of successful readings collected
                    break
            # Sleep before the next attempt
            sleep(sleep_time)

        if len(observed_values_list) >= required_successful_readings:
            # Compute the average across successful readings
            observed_values_over_time = np.array(observed_values_list)
            averaged_values = np.average(observed_values_over_time, axis=0)
            return {observable_names[k]: averaged_values[k] for k in range(len(observable_names))}
        else:
            # Insufficient successful readings collected
            print('Insufficient successful readings after 10 attempts. Returning zero values.')
            return {observable_name: 0.0 for observable_name in observable_names} 

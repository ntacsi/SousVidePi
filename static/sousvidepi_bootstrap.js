//
// Copyright (c) 2012-2014 Stephen P. Smith
//
// Permission is hereby granted, free of charge, to any person obtaining
// a copy of this software and associated documentation files
// (the "Software"), to deal in the Software without restriction,
// including without limitation the rights to use, copy, modify,
// merge, publish, distribute, sublicense, and/or sell copies of the Software,
// and to permit persons to whom the Software is furnished to do so,
// subject to the following conditions:

// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.

// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
// WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
// IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

//declare globals
var timeElapsed, tempDataArray, heatDataArray, setpointDataArray, dutyCycle, options_temp, options_heat, plot, gaugeDisplay, newGaugeDisplay;
var capture_on = 1;
var temp, setpoint;


$("#GPIO1").change(function() {

	if (this.checked) {
		jQuery.ajax({
			type : "GET",
			url : "/GPIO_Toggle/1/on",
			dataType : "json",
			async : true,
			cache : false,
			timeout : 50000,
			success : function(data) {
				$("#GPIO_label1").attr('title', 'Switch controls pin '+data.pin);
				if (data.status == "on") {	
					if ($("#GPIO_Color1").hasClass('btn-danger')) {
						$("#GPIO_Color1").removeClass('btn-danger');
						$("#GPIO_Color1").addClass('btn-success');
					}
				}
			},
		});
	} else {
		jQuery.ajax({
			type : "GET",
			url : "/GPIO_Toggle/1/off",
			dataType : "json",
			async : true,
			cache : false,
			timeout : 50000,
			success : function(data) {
				$("#GPIO_label1").attr('title', 'Switch controls pin '+data.pin);
				if (data.status == "off") {
					if ($("#GPIO_Color1").hasClass('btn-success')) {
						$("#GPIO_Color1").removeClass('btn-success');
						$("#GPIO_Color1").addClass('btn-danger');
					}
				}
			},
		});

	}
});

$("#GPIO2").change(function() {

	if (this.checked) {
		jQuery.ajax({
			type : "GET",
			url : "/GPIO_Toggle/2/on",
			dataType : "json",
			async : true,
			cache : false,
			timeout : 50000,
			success : function(data) {
				$("#GPIO_label2").attr('title', 'Switch controls pin '+data.pin);
				if (data.status == "on") {
					if ($("#GPIO_Color2").hasClass('btn-danger')) {
						$("#GPIO_Color2").removeClass('btn-danger');
						$("#GPIO_Color2").addClass('btn-success');
					}
				}
			},
		});
	} else {
		jQuery.ajax({
			type : "GET",
			url : "/GPIO_Toggle/2/off",
			dataType : "json",
			async : true,
			cache : false,
			timeout : 50000,
			success : function(data) {
				$("#GPIO_label2").attr('title', 'Switch controls pin '+data.pin);
				if (data.status == "off") {
					if ($("#GPIO_Color2").hasClass('btn-success')) {
						$("#GPIO_Color2").removeClass('btn-success');
						$("#GPIO_Color2").addClass('btn-danger');
					}
				}
			},
		});

	}
});

function findLS(selected_start, selected_end, in_pointArray) {

	var i;
	var values_x = [];
	var values_y = [];
	var in_pointArrayLength = in_pointArray.length;

	for ( i = 0; i < in_pointArrayLength; i++) {
		values_x.push(in_pointArray[i][0]);
		values_y.push(in_pointArray[i][1]);
	}

	var values_length = values_x.length;

	if (values_length != values_y.length) {
		throw new Error('x and y are not same size.');
	}

	if ((selected_start == 0) || (selected_end == 0)) {
		alert("Make a Selection");
	}
	// find indices	of selection
	var selection_start_index;
	var selection_end_index;
	var found_start = false;
	for ( i = 0; i < values_length; i++) {
		if ((values_x[i] >= selected_start) && (found_start == false)) {
			selection_start_index = i;
			found_start = true;
		}
		if (values_x[i] <= selected_end) {
			selection_end_index = i;
		}
	}

	var sum_x = 0;
	var sum_y = 0;
	var sum_xy = 0;
	var sum_xx = 0;
	var count = 0;
	var x = 0;
	var y = 0;
	/*
	 * Calculate the sum for each of the parts from imax to end
	 */
	for ( i = selection_start_index; i <= selection_end_index; i++) {
		x = values_x[i];
		y = values_y[i];
		sum_x += x;
		sum_y += y;
		sum_xx += x * x;
		sum_xy += x * y;
		count++;
	}

	/*
	 * Calculate m and b for the formula:
	 * y = x * m + b
	 */
	var m = (count * sum_xy - sum_x * sum_y) / (count * sum_xx - sum_x * sum_x);
	var b = (sum_y / count) - (m * sum_x) / count;

	var out_pointArray = [];

	for ( i = selection_start_index; i <= selection_end_index; i++) {
		x = values_x[i];
		y = m * x + b;
		out_pointArray.push([x, y]);
	}

	return [out_pointArray, m, b];
}

function showTooltip(x, y, contents) {
	jQuery('<div id="tooltip">' + contents + '</div>').css({
		position : 'absolute',
		display : 'none',
		top : y + 5,
		left : x + 5,
		border : '1px solid #fdd',
		padding : '2px',
		'background-color' : '#fee',
		opacity : 0.80
	}).appendTo("body").fadeIn(200);
}

function storeData(data) {

	setpointDataArray.push([timeElapsed, parseFloat(data.set_point)]);

	tempDataArray.push([timeElapsed, parseFloat(data.temp)]);
	heatDataArray.push([timeElapsed, parseFloat(data.duty_cycle)]);

	while (tempDataArray.length > jQuery('#windowSizeText').val()) {
		tempDataArray.shift();
	}

	while (heatDataArray.length > jQuery('#windowSizeText').val()) {
		heatDataArray.shift();
	}

	timeElapsed += parseFloat(data.elapsed);

	jQuery('#windowSizeText').change(function() {
		tempDataArray = [];
		heatDataArray = [];
		timeElapsed = 0;
	});
}

function plotData(index, data) {

	plot = jQuery.plot($("#tempplot"), [tempDataArray, setpointDataArray], options_temp);
	plot = jQuery.plot($("#heatplot"), [heatDataArray], options_heat);
}

//long polling - wait for message
function waitForMsg() {

	var className;

	jQuery.ajax({
		type : "GET",
		url : "/getstatus",
		dataType : "json",
		async : true,
		cache : false,
		timeout : 50000,

		success : function(data) {

			jQuery('#tempResponse').html(data.temp);
			jQuery('#modeResponse').html(data.mode);
			jQuery('#setpointResponse').html(data.set_point);
			jQuery('#dutycycleResponse').html(data.duty_cycle.toFixed(2));
			jQuery('#cycletimeResponse').html(data.cycle_time);
			jQuery('#k_paramResponse').html(data.k_param);
			jQuery('#i_paramResponse').html(data.i_param);
			jQuery('#d_paramResponse').html(data.d_param);

			storeData(0, data);

			if (capture_on == 1) {
				plotData(0, data);
				setTimeout('waitForMsg()', 1);
				//in millisec
			}
		}
	});
};

jQuery(document).ready(function() {

	jQuery('#stop').click(function() {
		capture_on = 0;
	});
	jQuery('#restart').click(function() {
		capture_on = 1;
		tempDataArray = [];
		heatDataArray = [];
		timeElapsed = [0];
		waitForMsg();
	});

	jQuery("#tempplot").bind("plotselected", function(event, ranges) {
		var selected_start = ranges.xaxis.from;
		var selected_end = ranges.xaxis.to;
		var k_param, i_param, d_param, normalizedSlope, pointArray, m, b, deadTime; 
		var LS = findLS(selected_start, selected_end, tempDataArray);
		pointArray = LS[0]; m = LS[1]; b = LS[2];
		deadTime = pointArray[0][0];
		normalizedSlope = m / jQuery('input:text[name=dutycycle]').val();
		jQuery('#deadTime').html(deadTime);
		jQuery('#normSlope').html(normalizedSlope);
		plot = jQuery.plot($("#tempplot"), [tempDataArray, pointArray], options_temp);
		k_param = 1.2 / (deadTime * normalizedSlope);
		i_param = 2.0 * deadTime;
		d_param = 0.5 * deadTime;
		jQuery('#Kc_tune').html(k_param.toFixed(2).toString());
		jQuery('#I_tune').html(i_param.toFixed(2).toString());
		jQuery('#D_tune').html(d_param.toFixed(2).toString());
	});

	var previousPoint = null;
	jQuery("#tempplot").bind("plothover", function(event, pos, item) {
		if (item) {
			if (previousPoint != item.dataIndex) {
				previousPoint = item.dataIndex;

				jQuery("#tooltip").remove();
				var x = item.datapoint[0].toFixed(2), y = item.datapoint[1].toFixed(2);

				showTooltip(item.pageX, item.pageY, "(" + x + ", " + y + ")");
			}
		} else {
			jQuery("#tooltip").remove();
			previousPoint = null;
		}
	});

	jQuery('#controlPanelForm').submit(function() {
		formdata = jQuery(this).serialize();

		//reset plot
		if (jQuery('#off').is(':checked') == false) {
			tempDataArray = [];
			heatDataArray = [];
			setpointDataArray = [];
			timeElapsed = [0];
		}

		return false;
	});

	// line plot Settings
	i = 0;
	tempDataArray = [];
	heatDataArray = [];
	setpointDataArray = [];
	timeElapsed = [0];

	options_temp = {
		series : {
			lines : {
				show : true
			},
			//points: {show: true},
			shadowSize : 0
		},
		yaxis : {
			min : null,
			max : null
		},
		xaxis : {
			show : true
		},
		grid : {
			hoverable : true
			//  clickable: true
		},
		selection : {
			mode : "x"
		}
	};

	options_heat = {
		series : {
			lines : {
				show : true
			},
			//points: {show: true},
			shadowSize : 0
		},
		yaxis : {
			min : 0,
			max : 100
		},
		xaxis : {
			show : true
		},
		selection : {
			mode : "x"
		}
	};

	waitForMsg();

});

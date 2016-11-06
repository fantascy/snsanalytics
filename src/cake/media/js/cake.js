function fbInit() {
	FB.init({
		appId  : FB_APP_ID,
		status : true, // check login status
		cookie : true, // enable cookies to allow the server to access the session
		xfbml  : true  // parse XFBML
	});
}

function jQueryDocReady() {
	$(".button").button();
	$("#cake-button a").button();
	bindOpenCloseButtonEvents();
	fitFrameSize();
	$(window).resize(fitFrameSize);
}

function pageWidth() {
	return window.innerWidth != null ? window.innerWidth : document.body != null ? document.body.clientWidth : null;
}
function pageHeight() {
	return window.innerHeight != null ? window.innerHeight : document.body != null ? document.body.clientHeight : null;
}

function fitFrameSize() {
	var windowWidth = pageWidth();
	var windowHeight = pageHeight();
	$('#main-container').outerWidth(windowWidth);
	$('#main-container').outerHeight(windowHeight);
	var sidebarWidth = $('#sidebar-frame').outerWidth();
	if (sidebarOpened) {
		$('#frame-container').outerWidth(windowWidth - sidebarWidth - 8);
	} else {
		$('#frame-container').outerWidth(windowWidth - 22);
	}
	$('#frame-container').outerHeight(windowHeight - 10);
	var maxImageWidth = windowWidth - sidebarWidth - 15;
	var maxImageHeight = windowHeight - 15;
	$('#frame-container img').css('max-width', maxImageWidth + 'px');
	$('#frame-container img').css('width', 'expression(this.width > ' + maxImageWidth + ' ? ' + maxImageWidth + ' : true)');
	$('#frame-container img').css('max-height', maxImageHeight + 'px');
	$('#frame-container img').css('height', 'expression(this.width > ' + maxImageHeight + ' ? ' + maxImageHeight + ' : true)');
	$('#sidebar-frame').outerHeight(windowHeight - 10);
	$('#sidebar-open-margin').outerHeight(windowHeight - 10);
	if (windowHeight > 720) 
		show(".screen-height-delta");
	else
		hide(".screen-height-delta");
}

function gotoTopicFramePage(topic){
	var topic = topic.value
	location.href ='/topic/' + topic + '/'
}

function bindOpenCloseButtonEvents() {
	$('#sidebar-open-margin').click(
		function () {
			$('#sidebar-frame').show();
			$(this).hide();
			sidebarOpened = true;
			fitFrameSize();
		});
	$('#sidebar-close-button').click(
		function () {
			window.location.href = $('#current-article-global-url').val();
			/*
			$('#sidebar-frame').hide();
			$('#sidebar-open-margin').show();
			sidebarOpened = false;
			fitFrameSize();
			*/
		});
	sidebarOpened = true;
}

function getCookie(name) {   
	 var nameEQ = name + "=";   
	 var ca = document.cookie.split(';');       
	 for(var i=0;i < ca.length;i++) {   
		 var c = ca[i];                         
		 while (c.charAt(0)==' ') {          
			 c = c.substring(1,c.length);     
		 }   
		 if (c.indexOf(nameEQ) == 0) {      
			 return unescape(c.substring(nameEQ.length,c.length));    
		 }   
	 }   
	 return null;   
} 

function setCookie(name, value, seconds) {   
	 seconds = seconds || 3600;   
	 var expires = "";   
	 if (seconds != 0 ) {      
		 var date = new Date();   
		 date.setTime(date.getTime()+(seconds*1000));   
		 expires = "; expires=" + date.toGMTString();   
	 }   
	 document.cookie = name+ "=" + escape(value) + expires + "; path=/";   
}  

function clearCookie(name) {   
 	setCookie(name, "", -1);   
}

function fbInit() {
	FB.init({
		appId  : FB_APP_ID,
		status : true, // check login status
		cookie : true, // enable cookies to allow the server to access the session
		xfbml  : true  // parse XFBML
	});
}

function countClick(id, url, surl, referrer){
	if (referrer.indexOf('snsanalytics.com')==-1){
		jQuery.post('/cake/click/', {id:id, url:url, surl:surl, referrer:referrer}, function(data) {
	  	});
	}
}

function toggleDialog(selector, showFunc) {
	obj = $(selector);
	if (obj.dialog("isOpen")==true) {
		obj.dialog("close");
	} else {
		showFunc(selector);
	}
}

function showHomeDialog(selector){
	$(selector).dialog({title:'Home', resizable : false, position: [250, 0], width: 500, show: 'slide', hide: 'slide', draggable: false});
}

function showDebugDialog(selector){
	$(selector).dialog({title:'Debug', resizable : false, position: [250, 150], width: 500, show: 'slide', hide: 'slide', draggable: false});
}

function showNoMoreArticleDialog(selector){
	$(selector).dialog({title:'Please Switch Topic!', resizable : false, position: [250, 100], width: 500, show: 'slide', hide: 'slide', draggable: false});
}

function showCommentDialog(selector) {
	if ($(selector).html() == '') {
		var url = $('#current-article-url').val();
		$(selector).html(
			'<fb:comments href="' + url + '" num_posts="5" width="500"></fb:comments>'
		);
		fbInit();
	}
	$(selector).dialog({resizable : false, position: [250, 150], width: 528, show: 'slide', hide: 'slide', draggable: false});
}

function showFeedbackDialog(selector) {
	$(selector).dialog({resizable : false, position: [250, 150], width: 460, show: 'slide', hide: 'slide'});
}

function showTopicDialog(selector) {
	$(selector).dialog({resizable : false, position: [250, 230], width: 750, show: 'slide', hide: 'slide'});
}

(function($) {
    $.fn.searchAndHighlight = function() {
        return this.each(function() {
        	var topic = $(this).html().toLowerCase();
        	var keyword = $('#topic-list-search-key').val().toLowerCase();
            if (keyword == '' || topic.indexOf(keyword) == -1) {
            	$(this).removeClass('highlight');
            } else {
            	$(this).addClass('highlight');
            }
        });
    };
})(jQuery);

function searchTopicList() {
	$('#topic-list .first-level a').searchAndHighlight();
	$('#topic-list li a').searchAndHighlight();
}

function pressEnter(e,id) { 
	if (e.keyCode == 13) { 
		$("#"+id).click();
	} 
} 

function topicAutoComplete(selector, topics ,type) {
	$(selector).autocomplete({
		delay : 0,
		source: function( request, response ) {
		 	var word = request.term.toLowerCase();
			var data = [];
			for(var i=0;i<topics.length;i++) {
			    name = topics[i].toLowerCase();
				if (name.indexOf(word) == 0 ){
					data.push(topics[i]);
				}
			}
			response(data);
		}
	});
	if (type == 1){
		$(selector).bind( "autocompleteselect",autoCompleteSelect )
	}
}

function gotoPage(page) {
	var location =  window.location;
	var url =  location.protocol + '//' +location.host + page;
	window.location.href = url;
}

function gotoTopicPage(topic) {
	var url = '/' +topic
	gotoPage(url);
}

function autoCompleteSelect(event, ui) {
   jQuery.get('/brew/topic/find/',{name:ui.item.value}, function(data) {
		gotoTopicPage(data)
	  });
}

function topicSearch() {
	var keyword = document.getElementById("topic-search-value").value;
	window.location.href = "/cake/topic/" + keyword;
}

function feedbackFormSubmit() {
    $.ajax({
         type: $("#feedback-form").attr("method"),
         url: $("#feedback-form").attr("action"),
         data: $("#feedback-form").serialize(),
         success: feedbackFormShowResponse
       });
}

function feedbackFormShowResponse() {
	$("#feedback-ack-msg").text("Your feedback is submitted. Thanks!").show().fadeOut(8000);
}

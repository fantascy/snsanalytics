var GLOBAL_TIMEOUT = 30000;

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
	$(".follow-button a").button();
	$(".topic-filter").buttonset();
	$(".search-element li").hover(
	    function() { $(this).addClass('ui-state-hover'); }, 
	    function() { $(this).removeClass('ui-state-hover'); }
	);
	$("#cse-search-action").click(cseSearch);
	$("#topic-search-action").click(topicSearch);
	$("#submit-article-thumbnails img").click(selectArticleThumbnail);
	$(".article-click-action").click(articleClick);
	FB.getLoginStatus(function(response) {
	  if (response.session) {
	  } else {
	  }
	});
	
	initDropdownMenu();
	initPlaceholder();
}

function jqueryLoad(selector, url) {
    $(selector).load(url);
}

function _ratingIconStar(selector) {
	$(selector).children().children().attr("class", "icon-16 icon-16-star-full");
}

function _ratingIconUnstar(selector) {
	$(selector).children().children().attr("class", "icon-16 icon-16-star-empty");
}

function ratingHoverIn() {
	var star = true; 
	var cursor = this;
	$(this).parent().children(".rating-login-user-icon").each(
		function() {
			if (star) {
				_ratingIconStar(this);
			} else {
				_ratingIconUnstar(this);
			}
			if (this==cursor) {
				star = false;
			}  
		});
}

function ratingHoverOut() {
	var index = $(this).parent().attr("orig");
	var star = true; 
	$(this).parent().children(".rating-login-user-icon").each(
		function() {
			if (index>0) {
				_ratingIconStar(this);
				index -= 1;
			} else {
				_ratingIconUnstar(this);
			}
		});
}

function ratingLogShowMore(keyname) {
	$('#rating-log-more').hide();
	var offset = document.getElementById('rating-offset').value
	jQuery.post("/brew/rate/log/", { offset: offset, keyname:keyname },
		  function(data){
		  	var text = document.getElementById('rating-log-all').innerHTML
		  	text = text + data
		    document.getElementById('rating-log-all').innerHTML=text
		    var newOff = parseInt(offset) + 2
		    document.getElementById('rating-offset').value = newOff
		    var count = document.getElementById('rating-count').value
		    if(newOff >= count){
		    } else {
		    	var more = Math.min(count-newOff, 2)
		    	document.getElementById('rating-more').innerHTML=more
		    	$('#rating-log-more').show();
		    }
		  });
}

function rateArticle(fbKey,selector, url){
	var cookie = document.cookie;
	if (cookie.indexOf(fbKey)!=-1 ) {
	  	$(selector).load(url);
	} else {
		soupSetData('selector',selector)
		soupSetData('url',url)
	    soupFbLogin(function(response) {
	    	if (response.session) {
	    	var selector = soupGetData('selector')
	    	var url = soupGetData('url')
	    	$(selector).load(url);
	    	}
	    });
	}
}

function deleteArticleConfirm(id) {
	$( '#delete-confirm-dialog-' + id ).dialog({resizable : false});
}

function deleteDialogClose(id) {
	$( '#delete-confirm-dialog-' + id ).dialog('close');
}

function deleteArticle(id) {
	$.ajax({
		url: '/brew/delete/?id=' + id,
		success: function(data) {
			if (data == 'success')
				window.location.reload();
			else if (data == 'already deleted') {
				$( '#delete-confirm-dialog-' + id ).dialog('close');
				$( '#already-deleted-dialog-' + id ).dialog({resizable : false});
			}
			else {
				$( '#delete-confirm-dialog-' + id ).dialog('close');
				$( '#delete-fail-dialog-' + id ).dialog({resizable : false});
			}
		},
		error: function() {
			$( '#delete-confirm-dialog-' + id ).dialog('close');
			$( '#delete-fail-dialog-' + id ).dialog({resizable : false});
		}
	});
}

function soupSetData(key,value){
	var input = document.getElementById('jquery-data')
	jQuery.data( input, key, value )
}

function soupGetData(key){
	var input = document.getElementById('jquery-data')
	return jQuery.data( input, key )
}

function ajaxUpdate(divSec, url, paraObject, method) {
    var divSec      = arguments[0];
    var url         = arguments[1];
    var paraObject;  
    if(arguments[2]==null) {
    	paraObject = "";
    } else {
    	paraObject = arguments[2];
    }
    
 	jQuery.ajax({
		  url: url,
		  type: method,
		  data: paraObject,
		  timeout:30000,
		  success: function(result, textStatus){
			document.getElementById(divSec).innerHTML=result;
		  },
		  error:function(){
		  },
		  complete:function(){
		  }
	});
}

function twitterDisconnect() {
  jQuery.post("/profile/twitter/disconnect/",
	  function(data){
	    window.location.href = "/settings/";
	  });
}

function soupSignOut(fbKey) {
	var cookie = document.cookie;
	if (cookie.indexOf(fbKey)!=-1 ) {
	  	FB.logout();
	} else {
	  	alert("You are not logged in!");
	}
}

function fbAuthLoginCallback() {
	if (soupGetData('pageReload')=='no'){
	} else {
		var url = location.href 
		location.href  = reloadUrl(url)
		soupSetData('pageReload','yes');
	}
	
}

function fbAuthLogoutCallback() {
	if (soupGetData('pageReload')=='no'){
	} else {
		var url = location.href 
		location.href  = reloadUrl(url)
		soupSetData('pageReload','yes');
	}
}

function reloadUrl(url){
	index = url.indexOf('?ref=invite')
	if (index!=-1){
		url = url.substring(0,index)
	}
	return url
}

function gotoPage(page) {
	var location =  window.location;
	var url =  location.protocol + '//' +location.host + page;
	window.location.href = url;
}

function gotoList(path,page){
	var url;
	if (path.indexOf('?')==-1){
		url = path + '?page=' + page;
	} else {
		url = path + '&page=' + page;
	}
	gotoPage(url);
}

function clickToPage(url, max){
	var page = document.getElementById('id_goToPages').value;
	if(!isNaN(page)){
		if(page - max > 0){
			page = max;
		}
		if(page - 1 < 0){
			page = 1;
		}
		gotoList(url,page);
	}
}

function pageOnClick(e,url, max) {
    if (e.keyCode == 13) { 
		clickToPage(url, max);
	} 
}

function gotoTopicPage(topic) {
	var url = '/' +topic
	gotoPage(url);
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

function chooseSoupType(type) {
	var type = type.value;
   	if (type==0) {
    	hide('#video-media');
    	show('#img-media');
    } else if (type==1) {
    	hide('#img-media');
    	show('#video-media');
    }
}

function chooseRankType(rankType) {
	setCookie("rankType",rankType);
	var topic = document.getElementById('current_topic').value;
	var mediaType = getCookie('mediaType');
	if (mediaType==null){
		mediaType = 'all';
	}
	if (rankType=='top') {
		var rankRange = getCookie('rankRange');
		if (rankRange==null){
			rankRange = 'week';
		}
		mediaType = mediaType + '/' + rankRange;
	}
	var url =  '/' + topic + '/' + rankType + '/' + mediaType;
	gotoPage(url);
}

function chooseMediaType(mediaType){
	setCookie("mediaType",mediaType);
	var topic = document.getElementById('current_topic').value;
	var rankType = getCookie('rankType');
	if (rankType==null){
		rankType = 'hot';
	}
	if (rankType=='top') {
		var rankRange = getCookie('rankRange');
		if (rankRange==null){
			rankRange = 'week';
		}
		mediaType = mediaType + '/' + rankRange;
	}
	var url = '/' + topic + '/' + rankType + '/' + mediaType;
	gotoPage(url);
}

function chooseRankRange(rankRange){
	setCookie("rankRange",rankRange);
	var topic = document.getElementById('current_topic').value;
	var rankType = getCookie('rankType');
	if (rankType==null) {
		rankType = 'hot';
	}
	var mediaType = getCookie('mediaType');
	if (mediaType==null) {
		mediaType = 'all';
	}
	if (rankType=='top') {
		mediaType = mediaType + '/' + rankRange;
	}
	var url = '/' + topic + '/' + rankType + '/' + mediaType;
	gotoPage(url);
}

function shareNewSoup() {
  var topic = document.getElementById('topic-input').value;
  var title = document.getElementById('title-input').value;
  jQuery.post("/submit/form/check/", { topic: topic, title:title },
			  function(data) {
			    if (data.indexOf("topic")!=-1) {
			    	show(document.getElementById('topic-not-exist'))
			    } 
			    if (data.indexOf("title")!=-1) {
			    	show(document.getElementById('title-required'))
			    } 
			    if (data.length==0) {
				    document.getElementById('shareSoup').submit();
			    }
			  });
}

function showShare(fbKey) {
  var cookie = document.cookie;
  if (cookie.indexOf(fbKey)==-1 ) {
        soupSetData('pageReload','no')
  		soupFbLogin(function(response) {
		    	if (response.session) {
		    		document.getElementById('share-link-form').submit();
		    	}
		    });
	} else{
	var link = document.getElementById('share_soup').value;
 	jQuery.post("/submit/check/", { link: link },
		  	  function(data) {
  				var type = data[0];
			    var data = data.slice(1);
			    dl = {};
			    type = parseInt(type);
			    if (type==0) {
			    	window.location.href = data;
			    } else if (type==1) {
				    dl['title'] = 'Error';
				    jQuery(data).dialog(dl);
			    } else if (type==2) {
				    document.getElementById('share-link-form').submit();
			    } 
			  });
	}

}

function editShare(id) {
	jQuery.post('/submit/update/', { id: id, reqtype: 'check' },
		function(data) {
			dl = {};
			if (data=='1') {
			    dl['title'] = 'Error';
			    jQuery(data).dialog(dl);
			} else {
				window.location.href = ('/submit/update/?id=' + id);
			}
		});
}

function followStatusLabel(followed) {
	return followed ? 'Unfollow' : 'Follow';
}

function toggleArticleFollow(articleId) {
	jQuery.getJSON("/brew/user/toggle_article_follow/", {id: articleId}, function(json) {
        result=json.result;
        if (result['toggled']) {
        	$('#article-follow-status-'+articleId + ' .ui-button-text').attr('innerHTML', followStatusLabel(result['followed']));
        }
	});
}

function headerNotice(msg) {
	document.getElementById("header-notice").innerHTML=msg;
	$("#header-notice").slideDown(800).delay(8000).slideUp(800);
}

function cseSearch() {
	document.getElementById('cse-search-box').submit();
}

function topicSearch() {
	var keyword = document.getElementById("topic-search-value").value;
	window.location.href = "/search/topic/?query=" + keyword;
}

function pressEnter(e,id) { 
	if (e.keyCode == 13) { 
		$("#"+id).click();
	} 
} 

function toggleImgMedia(check) {
	if (check.checked) {
		show('#submit-article-thumbnails');
	} else {
		hide('#submit-article-thumbnails');
	}
}

function selectArticleThumbnail() {
	$("#submit-article-thumbnails img.ui-state-active").removeClass("ui-state-active");
    $(this).addClass("ui-state-active");
    $("#submit-article input[name='picture']").attr('value', $(this).attr('src'));
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

function autoCompleteSelect(event, ui) {
   jQuery.get('/brew/topic/find/',{name:ui.item.value}, function(data) {
		gotoTopicPage(data)
	  });
}

function soupFbLoginCallback(){

}

function soupFbLogin(callback){
	FB.login(callback, {perms:'email,publish_stream,offline_access,user_location'});
}

function gotoFeelLucky(){
	jQuery.get('/brew/feellucky/', function(data) {
		gotoTopicPage(data)
	  });
}

function gotoLocal(){
	jQuery.get('/brew/local/', function(data) {
		gotoTopicPage(data)
	  });
}

function chooseProfileRank(uid,profileRank) {
	url = '/profile/'+ uid + '?atype=' + profileRank
	gotoPage(url)
}

function fbCommentCreate(response){
	var id = response.commentID
	var link = response.href
	var arr = link.split('/')
	var titleKey = arr[arr.length - 1]
	CommentCount.add(titleKey)
  	jQuery.post('/brew/comment/', {id:id , link:link, type:1},function(data) {
	  });
}

function fbCommentRemove(response){
	var id = response.commentID
	var link = response.href
	var arr = link.split('/')
	var titleKey = arr[arr.length - 1]
	CommentCount.minus(titleKey)
  	jQuery.post('/brew/comment/', {id:id , link:link, type:0},function(data) {
	  });
}

function fbFriendInvite(rel) {
	$("#fb-friend-invite .fb-friend-invite-one[rel='"+rel+"']").remove();
	show("#fb-friend-invite .fb-friend-invite-one.ui-helper-hidden:first");
}

function countClick(url,referrer){
	if (referrer.indexOf('snsanalytics.com')==-1){
		jQuery.post('/brew/click/', {url:url},function(data) {
	  	});
	}
	
}

function fbFriendInvite(count,id,name){
	jQuery.post('/profile/friend/invite/', {id:id,name:name},function(data) {
		hide(document.getElementById("friend-invite-"+count))
		try{
			var showId = document.getElementById("friend-invite-count").value
			show(document.getElementById("friend-invite-"+showId))
			document.getElementById("friend-invite-count").value = parseInt(showId) + 1
		}catch(err){
		}	
		if (data == 'fail'){
			msg = '<div>Oops. It looks like you have no more quota to invite friends. You can try tomorrow.</div>'
			jQuery(msg).dialog();
		}
	  });
}

function showComment(id) {
	if ($('#comment-' + id).html() == '') {
		$('#comment-' + id).html(
			'<fb:comments href="http://' + LONG_DOMAIN + '/soup/' + id +'" num_posts="5" width="550"></fb:comments>'
		);
		fbInit();
	}
	$('#comment-' + id).slideDown('fast');
	$('#show-' + id).hide();
	$('#count-' + id).hide();
	$('#hide-' + id).show();
};

function hideComment(id) {
	$('#comment-' + id).slideUp('fast');
	$('#hide-' + id).hide();
	$('#count-' + id).show();
	$('#show-' + id).show();
	$('#count-' + id).html('...');
	// Get comment count from client
	var count = CommentCount.get(id);
	if (count == 0)
		$('#count-' + id).html('');
	else
		$('#count-' + id).html('(' + count + ')');
	/*
	// Get comment count from server
	jQuery.get('/brew/getcommentcount/', { titlekey: id },
		function(count) {
			if (count == 0)
				$('#count-' + id).html('');
			else
				$('#count-' + id).html('(' + count + ')');
		}
	);
	*/
};

function showCommentVideo(id, line) {
	if (typeof(commentLineStatus) == "undefined") {
		commentLineStatus = new Array();
	}
	if (commentLineStatus[line]) {
		var openItemId = commentLineStatus[line];
		hideComment(openItemId);
	}
	commentLineStatus[line] = id;
	showComment(id);
}

function hideCommentVideo(id, line) {
	if (typeof(commentLineStatus) == "undefined") {
		alert('Function Error: commentLineStatus undefined!');
	}
	commentLineStatus[line] = undefined;
	hideComment(id);
}

function commentCountClosure() {
	var commentCount = new Array();
	function setCommentCount(id, number) {
		commentCount[id] = number;
		//alert("Set: " + id + " | " + commentCount[id]);
	}
	function getCommentCount(id) {
		//alert("Get: " + id + " | " + commentCount[id]);
		return commentCount[id];
	}
	function addCommentCount(id) {
		commentCount[id]++;
		//alert("Add: " + id + " | " + commentCount[id]);
	}
	function minusCommentCount(id) {
		commentCount[id]--;
		//alert("Minus: " + id + " | " + commentCount[id]);
	}
	return {set: setCommentCount, get: getCommentCount,
		add: addCommentCount, minus: minusCommentCount};
}

var CommentCount = commentCountClosure();

function initPlaceholder() {
	// Placeholder support
	jQuery.support.placeholder = false;
	test = document.createElement('input');
	if('placeholder' in test) jQuery.support.placeholder = true;
	if(!$.support.placeholder) { 
		var active = document.activeElement;
		$(':text').focus(function () {
			if ($(this).attr('placeholder') != '' && $(this).val() == $(this).attr('placeholder')) {
				$(this).val('').removeClass('hasPlaceholder');
			}
		}).blur(function () {
			if ($(this).attr('placeholder') != '' && ($(this).val() == '' || $(this).val() == $(this).attr('placeholder'))) {
				$(this).val($(this).attr('placeholder')).addClass('hasPlaceholder');
			}
		});
		$(':text').blur();
		$(active).focus();
		$('form:eq(0)').submit(function () {
			$(':text.hasPlaceholder').val('');
		});
	};
};

function initDropdownMenu() {
	// Initialize dropdown menu position
	var head_offset = $('#menu-head').offset();
	var head_width = $('#menu-head').width();
	var content_width = $('#menu-content').width();
	var content_offset = $('#menu-content').offset();
	$('#menu-content').css("left", head_offset.left + head_width - content_width + "px");
	// Add event to dropdown menu
	$('#dropdown-menu').bind('mouseover',function() 
	{
		$('#menu-content').slideDown('fast');
	}).bind('mouseleave',function()
	{
		$('#menu-content').slideUp('fast');
	});
	$('#menu-content').hide();
};

function friendsShowMore(pageSize) {
	$('#friends-more').hide();
	var offset = document.getElementById('friends-offset').value
	jQuery.post("/brew/user/friends/", { offset: offset },
		  function(data){
		  	var text = $('#user-friends').html();
		  	text = text + data;
		    $('#user-friends').html(text);
		    var newOff = parseInt(offset) + pageSize
		    document.getElementById('friends-offset').value = newOff
		    var count = document.getElementById('friends-count').value
		    if(newOff < count){
		    	$('#friends-more').show();
		    }
		  });
}

function articleClick(){
	var href = this.href
	var domain = 'http://' + LONG_DOMAIN + '/soup/'
	if (href.indexOf(domain)==0){
	} else{
		var url = this.name
		jQuery.post('/brew/click/', {url:url},function(data) {
	  	});
	}
	
}

function refreshParameterSetup(_topic, _mediaType) {
	var topic = _topic;
	var mediaType = _mediaType;
	var refreshNewArticles = function () {
		var lastRefreshTime = $('#last-refresh-time').val();
		jQuery.post('/brew/fresh/', { topic: topic, mediatype: mediaType, lastrefresh: lastRefreshTime },
			function(data){
				var i = data.indexOf('|');
				var j = data.indexOf('-') - 4;
				var time = data.substring(j, i);
				var text = data.substring(i + 1, data.length);
				i = text.indexOf('|');
				var number = parseInt(text.substring(0, i));
				if (number > 0)
					$('#article-new').slideDown('fast');
				text = text.substring(i + 1, text.length);
				$('#last-refresh-time').val(time);
				var old = parseInt($('#article-new-number').html());
				$('#article-new-number').html(old + number);
				if (text != 'none')
					$('#response-text').val(text + $('#response-text').val());
			});
	}
	return refreshNewArticles;
}

function showFreshArticles() {
	var text = $('#response-text').val();
	var orig = $('#article-more-container').html();
	$('#article-more-container').html(text + orig);
	$('#article-new-number').html(0);
	$('#response-text').val('');
	$('#article-new').hide();
}

function countDown(countSec, callFuncName) {
	var secRemain = $('#time-out').val();
	if (secRemain == 0) {
		this[callFuncName]();
		$('#time-out').val(countSec);
		return;
	}
	secRemain -= 1;
	$('#time-out').val(secRemain);
}
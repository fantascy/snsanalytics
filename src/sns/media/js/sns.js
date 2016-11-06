//for new code
var GLOBAL_TIMEOUT = 30000;
var ajaxProcessor;
var currrent_index = -1;
var image_links = null;

Array.prototype.append = function(arr) {
	for (var i = 0; i < arr.length; i++)
		this.push(arr[i]);
	return this;
}

function jQueryDocReady(){
	$('a[rel*=facebox]').facebox();

	$.history.init(function(url) {
    	page_load(url);
    });

	$('a[rel*=ajaxform]').each(function(){
		$(this).click(function(){

			var his = location.href;

			if(his.indexOf('#') > -1){
				var link = his.substring(his.indexOf('#'));
				if($(this).attr('href') == link){
					page_load(his);
				}
			}
			location.href = $(this).attr('href');
			// $.history.load(href);
			return false;
		});
	});
	
}

function ajaxUpdate(divSec, url, paraObject, method){
	
	
    var divSec      = arguments[0];
    
    if(!document.getElementById(divSec)){
    	return;
    }
    
    var url         = arguments[1];
    var paraObject;  
    if(arguments[2]==null){
    	paraObject="";
    }
    else{
    	paraObject= arguments[2];
    }
    if(method != 'GET'){
    	method = 'POST';
    }
    if(method=='GET'){
    	loading_start();
    }else{
    	document.getElementById(divSec).innerHTML = '<div id="ajax_loading_div"><div class="ajaxStateBar"><img src="'+commonImagePath("facebox/loading.gif")+'"/></div></div>';
    }
    
	jQuery.ajax({
		  url: url,
		  type: method,
		  data: paraObject,
		  timeout:GLOBAL_TIMEOUT,
		  success: function(result, textStatus){
			loading_complete();
			document.getElementById(divSec).innerHTML=result;
			
		    
		  },
		  error:function(XMLHttpRequest, textStatus, errorThrown){
			  loading_complete();
			  if(method=='GET'){
			        var a = XMLHttpRequest.status
			        if (a==404){
			           document.getElementById(divSec).innerHTML= errorPage('404');
			        }
			        else{
			           jQuery.facebox(errorPage(textStatus));
			        }
			    }else{
			    	document.getElementById(divSec).innerHTML= '<div class="ajaxStateBar">'+errorPage(textStatus)+'</div>';
			    }
			  
		  },
		  complete:function(result, textStatus){
			  pageRetrofit(jQuery('#'+divSec));
			  pageTracker._trackPageview(url);
			  var scripts = document.getElementById(divSec).getElementsByTagName("script"); 
			    for(var i=0;i<scripts.length;i++)
			    { 
			        eval(scripts[i].innerHTML); 
			    }
		  }
	});
}

function getTimeRange()
{
    if (document.getElementById('timeRange')) {
        return document.getElementById('timeRange').value;
    } else {
        return null;
    }
}


function getSurlReport(surl)
{
	url="/graph/chart?type=1&surl="+surl+"&timeRange="+getTimeRange()
	return window.location.href=url
}

function getUrlReport(url)
{
	url="/graph/chart?type=2&url="+url+"&timeRange="+getTimeRange()
	return window.location.href=url
}

function enterPress(e)
{ 
	if (e.keyCode == 13) { 
		document.getElementById('search_button').onclick()
	} 
} 


function goToPage(url, max){
	
	var page = document.getElementById('id_goToPages').value
	if(!isNaN(page)){
		if(page - max > 0){
			page = max;
		}
		if(page - 1 < 0){
			page = 1;
		}
		location.href = "#"+url+'&page='+page;
	}
	return false;
}

function pageOnClick(e,url, max)
{
    if (e.keyCode == 13) { 
		goToPage(url, max)
	} 
}

function changeListPage(page)
{
	var url =window.location.href;
	index = url.indexOf("page=")
	var redirect;
	if (index != -1){
		url = url.substring(0,index);
		redirect = url+'page='+page
	}
	else {
		if (url.indexOf("?")==-1){
			redirect = url + '?page='+page
		}
		else{
			redirect = url + '&page='+page
		}
	}
	
	return window.location.href=redirect
}

function searchList(url)
{
	var keyword=document.getElementById('query').value
	var action = url;
	if(url.indexOf('?')>0){
		action = url +"&query="+keyword;
	}else{
		action = url +"?query="+keyword;
	}
	location.href = "#" +action;
	
}

function searchList2(url) {
	var keyword=document.getElementById('query').value;
	var parts = url.split('&');
	var found = false;
	for (var i = 0; i < parts.length; i++) {
		if (parts[i].indexOf('keyword=') >= 0) {
			parts[i] = parts[i].substring(0, parts[i].indexOf('=') + 1) + keyword;
			found = true;
			break;
		}
	}
	var newUrl = parts.join('&');
	if (!found)
		newUrl += '&keyword=' + keyword;
	window.location.href = newUrl;
}

function searchSurl()
{
	document.getElementById('surl_search_error').style.display='none';
	var keyword=document.getElementById('urlHash').value;
	document.getElementById('search_result').innerHTML='';
	
	var html5=displayHtml5Define();
	
	jQuery.getJSON("/graph/surl/search",{ keyword: keyword}, function(json){
		  var surl=json.result
		  if (surl.length==0){
		  	  document.getElementById('toggleReportInfo').style.display='none';
			  document.getElementById('toggleReportHisDetail').style.display='none';
			  document.getElementById('surl_search_error').style.display='';
		  }
		  else if (surl.length==1){
		  	  document.getElementById('toggleReportInfo').style.display='';
			  document.getElementById('toggleReportHisDetail').style.display='';
			  document.getElementById('urlHash').value=surl[0]
			  updateShortUrlAll(html5);			  
		  }
		  else {
			  ajaxUpdate('search_result','/graph/surl/search/result',{data:surl.toString()})
			  ajaxUpdate('his_detail','/graph/chart/blank');
			  ajaxUpdate('info_detail','/graph/chart/blank');
		  }
			  
	});
}

function searchUrl()
{
	document.getElementById('url_search_error').style.display='none';
	var keyword=document.getElementById('url').value;
	document.getElementById('search_result').innerHTML='';
	
	var html5=displayHtml5Define();
	
	jQuery.getJSON("/graph/url/search",{ keyword: keyword}, function(json){
		  var url=json.result
		  if (url.length==0){
			  document.getElementById('toggleReportInfo').style.display='none';
			  document.getElementById('toggleReportHisDetail').style.display='none';
			  document.getElementById('url_search_error').style.display='';
		  }
		  else if (url.length==1){
		  	  document.getElementById('toggleReportInfo').style.display='';
			  document.getElementById('toggleReportHisDetail').style.display='';
			  document.getElementById('url').value=url[0]
			  updateUrlAll(html5)
		  }
		  else {
			  ajaxUpdate('search_result','/graph/url/search/result',{data:url.toString()})
			  ajaxUpdate('his_detail','/graph/chart/blank');
			  ajaxUpdate('info_detail','/graph/chart/blank');
		  }
			  
	});
}


function getSurlSearchReport(surl)
{
	html5=displayHtml5Define();
	document.getElementById('urlHash').value=surl;
	updateShortUrlAll(html5)
}

function getUrlSearchReport(url)
{
	html5=displayHtml5Define();
	document.getElementById('url').value=url;
	updateUrlAll(html5);
}


function toggleTimeRangeDisplay(timeRange)
{
	if(timeRange!=document.getElementById('timeRange').value){
	    document.getElementById(timeRange).style.backgroundColor = "#8EC1DA";
	    document.getElementById(timeRange).style.color = "#FFFFFF";
	    document.getElementById(document.getElementById('timeRange').value).style.backgroundColor = "#F3F9FC";
	    document.getElementById(document.getElementById('timeRange').value).style.color = "#000000";
	    document.getElementById('timeRange').value = timeRange
    }
}

function toggleTimeRangeRankingDisplay(timeRange)
{
    document.getElementById(timeRange+"_ranking").style.backgroundColor = "#8EC1DA";
    document.getElementById(timeRange+"_ranking").style.color = "#FFFFFF";
    document.getElementById(document.getElementById('timeRangeRanking').value+"_ranking").style.backgroundColor = "#F3F9FC";
    document.getElementById(document.getElementById('timeRangeRanking').value+"_ranking").style.color = "#000000";
    document.getElementById('timeRangeRanking').value = timeRange
}

function toggleInfoTypeDisplay(infoType)
{
	if(infoType!=document.getElementById('infoType').value){
		document.getElementById(infoType).style.backgroundColor = "#8EC1DA";
		document.getElementById(infoType).style.color = "#FFFFFF";
		document.getElementById(document.getElementById('infoType').value).style.backgroundColor = "#F3F9FC";
		document.getElementById(document.getElementById('infoType').value).style.color = "#000000";
		document.getElementById('infoType').value = infoType
	
	}
}

function getInfoType()
{
    if (document.getElementById('infoType')) {
        return document.getElementById('infoType').value;
    } else {
        return null
    }
}

function updateDMChart(infoType)
{
	toggleInfoTypeDisplay(infoType);
	
	var chartType = document.getElementById('chartType').value
	var turn = 0
	
	if (chartType==999){
	    var chartType='sendcount'
	}
	else {
	    var chartType='clickcount'
	}
	
	var id = document.getElementById('id').value
	var infoType = getInfoType()
	
	ajaxUpdate('info_detail','/dm/rule/chartdetail/',{chartType:chartType,infoType:infoType,id:id,turn:turn});
}

function updateReportInfo(infoType,initial)
{	
	var type=parseInt(document.getElementById('reportType').value);
	var html5=displayHtml5Define();
	
	if(type==0){
		updateUserInfo(infoType,initial,html5);
	}
	else if(type==1){
		updateSurlInfo(infoType,initial,html5);
	}
	else if(type==2){
		updateUrlInfo(infoType,initial,html5);
	}
	else if(type==3){	
		updateChannelInfo(infoType,initial,html5);
	}
	else if(type==4){
		updateFeedInfo(infoType,initial,html5);
	}
	else if(type==5){
		updateCampaignInfo(infoType,initial,html5);
	}
	else if(type==7){
		updateFChannelInfo(infoType,initial,html5);
	}
	else if(type==8){
		updateDirectInfo(infoType,initial,html5);
	}
}

function updateReportHisDetailT(timeRange)
{	
	var type=parseInt(document.getElementById('reportType').value);
	var html5=displayHtml5Define();
	if(type==0){
		updateUserHisDetailT(timeRange,html5);
	}
	else if(type==1){
		updateShortUrlHisDetailT(timeRange,html5);
	}
	else if(type==2){
		updateUrlHisDetailT(timeRange,html5);
	}
	else if(type==3){	
		updateChannelHisDetailT(timeRange,html5);
	}
	else if(type==4){
		updateFeedHisDetailT(timeRange,html5);
	}
	else if(type==5){
		updateCampaignHisDetailT(timeRange,html5);
	}
	else if(type==7){
		updateFChannelHisDetailT(timeRange,html5);
	}
	else if(type==8){
		updateCampaignHisDetailT(timeRange,html5);
	}
}

function updateUserInfo(infoType,initial,html5)
{
	if(initial==true){
		infoType=getInfoType()
	}
	else {
		toggleInfoTypeDisplay(infoType);
	}
	if(html5){
		if (infoType=='information'){
			ajaxUpdate('info_detail','/graph/user/info/detail',{infoType:getInfoType()})
		}
		else if(infoType=='country'){
			ajaxUpdate('info_detail','/graph/user/info/html5',{infoType:getInfoType()})
		}
		else if(infoType=='referrer'){
			ajaxUpdate('info_detail','/graph/user/info/html5',{infoType:getInfoType()})
		}
	}
	else{	
		if (infoType=='information'){
			ajaxUpdate('info_detail','/graph/user/info/detail',{infoType:getInfoType()})
		}
		else if(infoType=='country'){
			ajaxUpdate('info_detail','/graph/user/info/country',{infoType:getInfoType()})
		}
		else if(infoType=='referrer'){
			ajaxUpdate('info_detail','/graph/user/info/referrer',{infoType:getInfoType()})
		}
	}	
}

function updateSurlInfo(infoType,initial,html5)
{
	if(initial==true){
		infoType=getInfoType()
	}
	else{
	toggleInfoTypeDisplay(infoType);
	}
	var urlHash=document.getElementById('urlHash').value
	if (infoType=='information'){
		ajaxUpdate('info_detail','/graph/surl/info/detail',{infoType:getInfoType(),urlHash: urlHash})
	}
	else if(infoType=='country'){
		if(html5){
			ajaxUpdate('info_detail','/graph/surl/info/html5',{infoType:getInfoType(),urlHash: urlHash});
		}
		else{
			ajaxUpdate('info_detail','/graph/surl/info/country',{infoType:getInfoType(),urlHash: urlHash});		
		}
	}
	else if(infoType=='referrer'){
		if(html5){
			ajaxUpdate('info_detail','/graph/surl/info/html5',{infoType:getInfoType(),urlHash: urlHash});
		}
		else{
			ajaxUpdate('info_detail','/graph/surl/info/referrer',{infoType:getInfoType(),urlHash: urlHash});		
		}		
	}
	
	
}

function updateUrlInfo(infoType,initial,html5)
{
	if(initial==true){
		infoType=getInfoType()
	}
	else{
		toggleInfoTypeDisplay(infoType);
	}
	var url=document.getElementById('url').value
	if (infoType=='information'){
		ajaxUpdate('info_detail','/graph/url/info/detail',{infoType:getInfoType(),url: url})
	}
	else if(infoType=='country'){
		if(html5){
			ajaxUpdate('info_detail','/graph/url/info/html5',{infoType:getInfoType(),url: url});
		}
		else{
			ajaxUpdate('info_detail','/graph/url/info/country',{infoType:getInfoType(),url: url});	
		}
	}
	else if(infoType=='referrer'){
		if(html5){
			ajaxUpdate('info_detail','/graph/url/info/html5',{infoType:getInfoType(),url: url});
		}
		else{
			ajaxUpdate('info_detail','/graph/url/info/referrer',{infoType:getInfoType(),url: url});	
		}
		
	}
		
}

function updateChannelInfo(infoType,initial,html5)
{
	if(initial==true){
		infoType=getInfoType()
		channel=document.getElementById('channel_value').value
	}
	else{
		toggleInfoTypeDisplay(infoType);
		channel=document.getElementById('channel').value
	}
	
	if (infoType=='information'){
		ajaxUpdate('info_detail','/graph/channel/info/detail',{infoType:getInfoType(),channel: channel})
	}
	else if(infoType=='country'){
		if(html5){
			ajaxUpdate('info_detail','/graph/channel/info/html5',{infoType:getInfoType(),channel: channel});
		}
		else{		
			ajaxUpdate('info_detail','/graph/channel/info/country',{infoType:getInfoType(),channel: channel});		
		}
	}
	else if(infoType=='referrer'){
		if(html5){
			ajaxUpdate('info_detail','/graph/channel/info/html5',{infoType:getInfoType(),channel: channel});
		}
		else{		
			ajaxUpdate('info_detail','/graph/channel/info/referrer',{infoType:getInfoType(),channel: channel});		
		}
		
	}
		
}

function updateFChannelInfo(infoType,initial,html5)
{
	if(initial==true){
		infoType=getInfoType();
		fchannel=document.getElementById('fchannel_value').value;
	}
	else{
		toggleInfoTypeDisplay(infoType);
		fchannel=document.getElementById('fchannel').value;
	}
	
	if (infoType=='information'){
		ajaxUpdate('info_detail','/graph/fchannel/info/detail',{infoType:getInfoType(),fchannel: fchannel})
	}
	else if(infoType=='country'){
		if(html5){
			ajaxUpdate('info_detail','/graph/fchannel/info/html5',{infoType:getInfoType(),fchannel: fchannel});
		}
		else{
			ajaxUpdate('info_detail','/graph/fchannel/info/country',{infoType:getInfoType(),fchannel: fchannel});
		}		
	}
	else if(infoType=='referrer'){
		if(html5){
			ajaxUpdate('info_detail','/graph/fchannel/info/html5',{infoType:getInfoType(),fchannel: fchannel});
		}
		else{
			ajaxUpdate('info_detail','/graph/fchannel/info/referrer',{infoType:getInfoType(),fchannel: fchannel});
		}		
	}
		
}

function updateFeedInfo(infoType,initial,html5)
{
	if(initial==true){
		infoType=getInfoType()
		feed=document.getElementById('feed_value').value
	}
	else{
		toggleInfoTypeDisplay(infoType);
		feed=document.getElementById('feed').value
	}
	
	if (infoType=='information'){
		ajaxUpdate('info_detail','/graph/feed/info/detail',{infoType:getInfoType(),feed: feed})
	}
	else if(infoType=='country'){
		if(html5){
			ajaxUpdate('info_detail','/graph/feed/info/html5',{infoType:getInfoType(),feed: feed});
		}
		else{		
			ajaxUpdate('info_detail','/graph/feed/info/country',{infoType:getInfoType(),feed: feed});		
		}
	}
	else if(infoType=='referrer'){
		if(html5){
			ajaxUpdate('info_detail','/graph/feed/info/html5',{infoType:getInfoType(),feed: feed});
		}
		else{		
			ajaxUpdate('info_detail','/graph/feed/info/referrer',{infoType:getInfoType(),feed:feed});		
		}		
	}
		
}

function updateCampaignInfo(infoType,initial,html5)
{
	if(initial==true){
		infoType=getInfoType()
		campaign=document.getElementById('campaign_value').value
	}
	else{
		toggleInfoTypeDisplay(infoType);
		try{
		campaign=document.getElementById('campaign').value
		}
		catch(err){
		campaign=document.getElementById('direct_value').value
		}
	}
	if (infoType=='information'){
		ajaxUpdate('info_detail','/graph/campaign/info/detail',{infoType:getInfoType(),campaign: campaign})
	}
	else if(infoType=='country'){
		if(html5){
			ajaxUpdate('info_detail','/graph/campaign/info/html5',{infoType:getInfoType(),campaign: campaign});
		}
		else{
			ajaxUpdate('info_detail','/graph/campaign/info/country',{infoType:getInfoType(),campaign: campaign});
		}
	}
	else if(infoType=='referrer'){
		if(html5){
			ajaxUpdate('info_detail','/graph/campaign/info/html5',{infoType:getInfoType(),campaign: campaign});
		}
		else{
			ajaxUpdate('info_detail','/graph/campaign/info/referrer',{infoType:getInfoType(),campaign:campaign});
		}		
	}
		
}

function updateDirectInfo(infoType,initial,html5)
{
	if(initial!=true){
		toggleInfoTypeDisplay(infoType);
	}
	campaign=document.getElementById('direct_value').value
	infoType=getInfoType()
	if (infoType=='information'){
		ajaxUpdate('info_detail','/graph/campaign/info/detail',{infoType:getInfoType(),campaign: campaign})
	}
	else if(infoType=='country'){
		if(html5){
			ajaxUpdate('info_detail','/graph/campaign/info/html5',{infoType:getInfoType(),campaign: campaign});
		}
		else{
			ajaxUpdate('info_detail','/graph/campaign/info/country',{infoType:getInfoType(),campaign: campaign});
		}		
	}
	else if(infoType=='referrer'){
		if(html5){
			ajaxUpdate('info_detail','/graph/campaign/info/html5',{infoType:getInfoType(),campaign: campaign});
		}
		else{
			ajaxUpdate('info_detail','/graph/campaign/info/referrer',{infoType:getInfoType(),campaign:campaign});
		}			
	}
		
}

function updateShortUrlAll(html5)
{
	updateShortUrlHisDetail(html5);
	updateSurlInfo('',true,html5);
}

function updateUrlAll(html5)
{
	updateUrlHisDetail(html5);
	updateUrlInfo('',true,html5);
}

function updateChannelAll()
{
	var html5=displayHtml5Define();
	updateChannelHisDetail(html5);
	updateChannelInfo(getInfoType(),false,html5);
}

function updateFeedAll()
{
	var html5=displayHtml5Define();
	updateFeedHisDetail(html5);
	updateFeedInfo(getInfoType(),false,html5);
}

function updateCampaignAll()
{
	var html5=displayHtml5Define();
	updateCampaignHisDetail(html5);
	updateCampaignInfo(getInfoType(),false,html5);
}

function updateShortUrlHisDetail(html5)
{	
	if(html5){
		ajaxUpdate('his_detail','/graph/surl/chart/detail/html5',{urlHash: document.getElementById('urlHash').value, timeRange: getTimeRange()});
	}
	else{
		ajaxUpdate('his_detail','/graph/surl/chart/detail',{urlHash: document.getElementById('urlHash').value, timeRange: getTimeRange()});
	}    
}

function updateShortUrlHisDetailT(timeRange,html5)
{
    toggleTimeRangeDisplay(timeRange);
    updateShortUrlHisDetail(html5);
}

function updateHomeHisDetail()
{
	ajaxUpdate('his_detail','/dashboard/chart/html5',{urlHash:null, timeRange: getTimeRange()});
}

function updateHomeHisDetailT(timeRange)
{
    toggleTimeRangeDisplay(timeRange);
    updateHomeHisDetail();
}

function updateUserHisDetail(html5){
	if(html5){
		ajaxUpdate('his_detail','/graph/user/chart/detail/html5',{urlHash: null, timeRange: getTimeRange()});	
	}
	else{	
		ajaxUpdate('his_detail','/graph/user/chart/detail',{urlHash: null, timeRange: getTimeRange()});	
	}
}

function updateUserHisDetailT(timeRange,html5){
    toggleTimeRangeDisplay(timeRange);
    updateUserHisDetail(html5);	
}

function updateUrlHisDetail(html5)
{
	if(html5){
		ajaxUpdate('his_detail','/graph/url/chart/detail/html5',{url: document.getElementById('url').value, timeRange: getTimeRange()});
	}
	else{
		ajaxUpdate('his_detail','/graph/url/chart/detail',{url: document.getElementById('url').value, timeRange: getTimeRange()});
	
	}    
}

function updateUrlHisDetailT(timeRange,html5)
{
    toggleTimeRangeDisplay(timeRange);
    updateUrlHisDetail(html5);
}

function updateChannelHisDetail(html5)
{
	if(!html5){
		html5=displayHtml5Define();
	}
	var channel = document.getElementById('channel').value
	var channelCompare = document.getElementById('channel_compare').value
	if(html5){
		ajaxUpdate('his_detail','/graph/channel/chart/detail/html5',{channel: channel, channelCompare:channelCompare, timeRange: getTimeRange()})
	}
	else{
	 	ajaxUpdate('his_detail','/graph/channel/chart/detail',{channel: channel, channelCompare:channelCompare, timeRange: getTimeRange()})
	}   
}

function updateChannelHisDetailT(timeRange,html5)
{
    toggleTimeRangeDisplay(timeRange);
    updateChannelHisDetail(html5);
}

function updateFeedHisDetail(html5)
{
	if(!html5){
		html5=displayHtml5Define();
	}
	if(html5){
		ajaxUpdate('his_detail','/graph/feed/chart/detail/html5',{feed: document.getElementById('feed').value, feedCompare:document.getElementById('feed_compare').value, timeRange: getTimeRange()})
	}
	else{    
		ajaxUpdate('his_detail','/graph/feed/chart/detail',{feed: document.getElementById('feed').value, feedCompare:document.getElementById('feed_compare').value, timeRange: getTimeRange()})
	}
}

function updateFeedHisDetailT(timeRange,html5)
{
    toggleTimeRangeDisplay(timeRange);
    updateFeedHisDetail(html5);
}

function updateCampaignHisDetail(html5)
{
    try {
    var campaign = document.getElementById('campaign').value
	var campaignCompare = document.getElementById('campaign_compare').value
    }
    catch(err){
    var campaign = document.getElementById('direct_value').value
    var campaignCompare = 'None'
    }
    if(!html5){
		html5=displayHtml5Define();
	}
    if(html5){	
    	ajaxUpdate('his_detail','/graph/campaign/chart/detail/html5',{campaign: campaign,campaignCompare : campaignCompare, timeRange: getTimeRange()})
	}
	else{
    	ajaxUpdate('his_detail','/graph/campaign/chart/detail',{campaign: campaign,campaignCompare : campaignCompare, timeRange: getTimeRange()})
	}
}

function updateCampaignHisDetailT(timeRange,html5)
{
    toggleTimeRangeDisplay(timeRange);
    updateCampaignHisDetail(html5);
}

function updateChannelFailureHisDetail()
{
	channel=document.getElementById('channelFailure').value
	url='/graph/postfailurelist/channel?channel='+channel
	ajaxUpdate('his_detail',url)
	document.getElementById('his_detail_url').value=url
}

function updateFChannelFailureHisDetail()
{
	fchannel=document.getElementById('fchannelFailure').value
	url='/graph/postfailurelist/fchannel?fchannel='+fchannel
	ajaxUpdate('his_detail',url)
	document.getElementById('his_detail_url').value=url
}

function updateMessageFailureHisDetail()
{
	article=document.getElementById('articleFailure').value
	url='/graph/postfailurelist/article?article='+article
	ajaxUpdate('his_detail',url)
	document.getElementById('his_detail_url').value=url
}

function updateFeedFailureHisDetail()
{
	feed=document.getElementById('feedFailure').value
	url='/graph/postfailurelist/feed?feed='+feed
	ajaxUpdate('his_detail',url)
	document.getElementById('his_detail_url').value=url
}

function updateCampaignFailureHisDetail()
{
	campaign=document.getElementById('campaignFailure').value
	url='/graph/postfailurelist/campaign?campaign='+campaign
	ajaxUpdate('his_detail',url)
	document.getElementById('his_detail_url').value=url
}

function getReportFailureDetailUrl(){
	var type=document.getElementById('report_failure_type');
	var url;
	if (type.value==0){
		url='/graph/postfailurelist/all';
	}
	else if (type.value==1){
		var channel=document.getElementById('channelFailure').value;
		if(channel==''){
			url='/graph/postfailurelist/channel?channel=';
		}
		else{
			url='/graph/postfailurelist/channel?channel='+channel;
		}
	}
	else if (type.value==2){
		article=document.getElementById('articleFailure').value
		if (article==''){
			url='/graph/postfailurelist/channel?channel='
		}
		else {
			url='/graph/postfailurelist/article?article='+article
		}		
	}
	else if (type.value==3){
		feed=document.getElementById('feedFailure').value
		if (feed==''){
			url='/graph/postfailurelist/channel?channel='
		}
		else {
			url='/graph/postfailurelist/feed?feed='+feed
		}		
	}
	else if (type.value==4){
		campaign=document.getElementById('campaignFailure').value
		if (campaign==''){
			url='/graph/postfailurelist/channel?channel='
		}
		else {
			url='/graph/postfailurelist/campaign?campaign='+campaign
		}		
	}
	
	else if (type.value==5){
		fchannel=document.getElementById('fchannelFailure').value
		if (fchannel==''){
			url='/graph/postfailurelist/channel?channel='
		}
		else {
			url='/graph/postfailurelist/fchannel?fchannel='+fchannel
		}		
	}
	return url;
	
}

function chooseReportFailureDetailTypePage(page,paginate_by)
{
	var url = getReportFailureDetailUrl();
	if(url.indexOf('?')==-1){
		url=url+'?paginate_by='+paginate_by+'&page='+page;
	}
	else{
		url=url+'&paginate_by='+paginate_by+'&page='+page;
	}
	ajaxUpdate('his_detail',url);
	document.getElementById('his_detail_url').value=url;
}

function chooseReportFailureDetailTypeCertainPage(paginate_by)
{
	var url = getReportFailureDetailUrl();
	var page=document.getElementById('id_goToPages').value;
	if(url.indexOf('?')==-1){
		url=url+'?paginate_by='+paginate_by+'&page='+page;
	}
	else{
		url=url+'&paginate_by='+paginate_by+'&page='+page;
	}
	ajaxUpdate('his_detail',url);
    document.getElementById('his_detail_url').value=url;
}


function chooseFollowType(type)
{
    var id=document.getElementById('id').value
    var infoType = getInfoType()
    if (type.value==0){
        var chartType = 'follower'
	}
	if (type.value==1){
	    var chartType = 'follow'
	}
	if (type.value==2){
	    var chartType = 'both'
	} 
	ajaxUpdate('info_detail','/fe/follow/account/chartdetail',{id:id,chartType:chartType,infoType:infoType});

}

function chooseDMChartType(type)
{
    var id=document.getElementById('id').value
    var infoType = getInfoType()
    if (type.value==999){
        var chartType = 'sendcount'
        ajaxUpdate('info_count','/dm/rule/sendcount/',{id:id});
        ajaxUpdate('info_detail','/dm/rule/chartdetail/',{id:id,chartType:chartType,infoType:infoType});
	}
	else {
	    var chartType = 'clickcount'
	    var turn = type.value
	    ajaxUpdate('info_count','/dm/rule/clickcount/',{id:id,turn:turn});
	    ajaxUpdate('info_detail','/dm/rule/chartdetail/',{id:id,chartType:chartType,infoType:infoType,turn:turn});
	}
	

}

function chooseReportType(type)
{	
	document.getElementById('toggleReportInfo').style.display='';
	document.getElementById('toggleReportHisDetail').style.display='';
	document.getElementById('reportType').value=type.value;
	if (type.value==0){	
		ajaxUpdate('top_form','/graph/user/chart/topform');
		ajaxUpdate('his_detail','/graph/user/chart/detail/html5',{urlHash: null, timeRange: getTimeRange()});
		updateUserInfo('',true,true);
	}
	else if (type.value==1){
		if (document.getElementById('surl_value').value==''){
			document.getElementById('toggleReportInfo').style.display='none';
			document.getElementById('toggleReportHisDetail').style.display='none';
			ajaxUpdate('top_form','/graph/surl/chart/topform');
			ajaxUpdate('his_detail','/graph/chart/blank');
			ajaxUpdate('info_detail','/graph/chart/blank');
		}
		else {
			document.getElementById('toggleReportInfo').style.display='';
			document.getElementById('toggleReportHisDetail').style.display='';
			urlHash=document.getElementById('surl_value').value
			ajaxUpdate('top_form','/graph/surl/chart/topform?surl='+urlHash);
			ajaxUpdate('his_detail','/graph/surl/chart/detail/html5',{urlHash: urlHash, timeRange: getTimeRange()})
			if(getInfoType()=='information'){
				ajaxUpdate('info_detail','/graph/surl/info/detail',{urlHash: urlHash, infoType:getInfoType()});
			}
			else{
				ajaxUpdate('info_detail','/graph/surl/info/html5',{urlHash: urlHash, infoType:getInfoType()});
			}		
			document.getElementById('surl_value').value=''
		}		
	}
	else if (type.value==2){
		if (document.getElementById('url_value').value==''){
			document.getElementById('toggleReportInfo').style.display='none';
			document.getElementById('toggleReportHisDetail').style.display='none';
			ajaxUpdate('top_form','/graph/url/chart/topform');
			ajaxUpdate('his_detail','/graph/chart/blank');
			ajaxUpdate('info_detail','/graph/chart/blank');
		}
		else {
			document.getElementById('toggleReportInfo').style.display='';
			document.getElementById('toggleReportHisDetail').style.display='';
			url=document.getElementById('url_value').value
			ajaxUpdate('top_form','/graph/url/chart/topform?url='+escape(url));
			ajaxUpdate('his_detail','/graph/url/chart/detail/html5',{url: url, timeRange: getTimeRange()})
			if(getInfoType()=='information'){
				ajaxUpdate('info_detail','/graph/url/info/detail',{url: url, infoType:getInfoType()});
			}
			else{
				ajaxUpdate('info_detail','/graph/url/info/html5',{url: url, infoType:getInfoType()});
			}	
			document.getElementById('url_value').value=''
		}		
	}
	else if (type.value==3){
		var channel = document.getElementById('channel_value').value;
		var channelCompare = 'None'
		ajaxUpdate('top_form','/graph/channel/chart/topform',{channel: channel});
		ajaxUpdate('his_detail','/graph/channel/chart/detail/html5',{channel: channel,channelCompare : channelCompare, timeRange: getTimeRange()})
		updateChannelInfo('',true,true)
	}
	else if (type.value==4){
		var feed = document.getElementById('feed_value').value;
		var feedCompare = 'None'
		ajaxUpdate('top_form','/graph/feed/chart/topform',{feed: feed});
		ajaxUpdate('his_detail','/graph/feed/chart/detail/html5',{feed: feed, feedCompare : feedCompare, timeRange: getTimeRange()})
		updateFeedInfo('',true,true)
	}
	else if (type.value==5){
		var campaign = document.getElementById('campaign_value').value;
		var campaignCompare = 'None'
		ajaxUpdate('top_form','/graph/campaign/chart/topform',{campaign: campaign});
		ajaxUpdate('his_detail','/graph/campaign/chart/detail/html5',{campaign: campaign,campaignCompare: campaignCompare, timeRange: getTimeRange()})
		updateCampaignInfo('',true,true)
	}
	else if (type.value==7){
		var fchannel = document.getElementById('fchannel_value').value;
		var fchannelCompare = 'None'
		ajaxUpdate('top_form','/graph/fchannel/chart/topform',{fchannel: fchannel});
		ajaxUpdate('his_detail','/graph/fchannel/chart/detail/html5',{fchannel: fchannel,fchannelCompare : fchannelCompare, timeRange: getTimeRange()})
		updateFChannelInfo('',true,true)
	}	
	else if (type.value==8){
		var campaign = document.getElementById('direct_value').value;
		var campaignCompare = 'None'
		ajaxUpdate('top_form','/graph/chart/blank');
		updateDirectInfo('',true,true)
		ajaxUpdate('his_detail','/graph/campaign/chart/detail/html5',{campaign: campaign,campaignCompare: campaignCompare, timeRange: getTimeRange()});
	}
}

function chooseMsgType(type){
   if (type.value==0){
      var info = $('#id_info').text();
      count = parseInt(info) -280;
      $('#id_info').empty();
      $('#id_info').append(count);
   }
   if (type.value==1){
	  var info = $('#id_info').text();
      count = parseInt(info) + 280;
      $('#id_info').empty();
      $('#id_info').append(count);
   }
   

}

function choosePostToType(type,initial){
	var id = $(type).attr('id');
	var checked = $(type).is(":checked");
	if (!checked){
		if(id == 'is_twitter'){
			$('option[value=0]','#id_type').attr('selected',false);
			
			$('#id_channels').val(null);
			$('#channels_info').hide();
		} else if(id == 'is_facebook'){
			
			$('option[value=1]','#id_type').attr('selected',false);
			
			var info = $('#id_info').text();
			var count = parseInt(info) -280;
		    $('#id_info').empty();
		    $('#id_info').append(count);

			
		    $('#fchannels_info').hide();
		    $('#id_fbDestinations').val(null);
		    $('input',$('#fchannels_info')).val(null);
		    $('#link_attchment').hide();
		    $('#is_attach').attr('checked', false);
		    $('input',$('#link_detail')).val(null);
			
			$('#id_pic_info_current').text(1);
			$('#id_pic_info_total').text(0);
			image_links=null;
			$('#link_detail').hide();
		}
	}else { 
		if(id == 'is_twitter'){
			$('option[value=0]','#id_type').attr('selected',true);
			if(document.getElementById('twitter_count').value=='1'){
				document.getElementById('id_channels').options[0].selected=true;
			}
			$('#channels_info').show();
		} else if(id == 'is_facebook'){
			
			$('option[value=1]','#id_type').attr('selected',true);
			if(document.getElementById('facebook_count').value=='1'){
				document.getElementById('id_fbDestinations').options[0].selected=true;
			}
			
			if(!initial){
				var info = $('#id_info').text();
				var count = parseInt(info) + 280;
				$('#id_info').empty();
				$('#id_info').append(count);
			}			

		    $('#fchannels_info').show();
		    
		    if($('#id_url').val()){
		    	$('#link_attchment').show();
		    }
		    
		    
		}
	} 
}

function chooseRankingType(type,color,limit,home)
{	
	if (color==true) {
		toggleTimeRangeRankingDisplay(type);
	}
	var url;
    if (type=='hour'){
    	url='/graph/clickranking/hour?limit='+limit
    }
	else if (type=='day'){
		url='/graph/clickranking/today?limit='+limit
	}
	else if (type=='week'){
		url='/graph/clickranking/week?limit='+limit
	}
	else if (type=='month'){
		url='/graph/clickranking/month?limit='+limit
	}
	else if (type=='max'){
		url='/graph/clickranking/lifetime?limit='+limit
	}

    url=url+'&home='+home;
    
    ajaxUpdate('his_detail_home',url);
    document.getElementById('his_detail_url').value=url
	
}


function chooseBotType(type,color)
{
	if (color==true) {
		toggleInfoTypeDisplay(type);
	}
    ajaxUpdate('his_detail','/log/blacklist/table?type='+type);

}

function chooseUserCount(type)
{
	var type = type.value
	url = '/usr/list_body_by_click/?type='+type
	ajaxUpdate('his_detail',url);
	document.getElementById('his_detail_url').value=url
}

function chooseUserDate(type)
{
	var type = type.value
	url = '/usr/list_body_by_date/?type='+type
	ajaxUpdate('his_detail',url);
	document.getElementById('his_detail_url').value=url
}

function chooseStatsType(type){
	var type = type.value
	window.location.href = '/#/log/stats/?type='+type
}

function chooseChannelStatsType(type){
	var id = $('#id').val();
	window.location.href = '/#/log/channelchart/?id=' + id + '&chartType='+ type.value;
}

function chooseContentSourceStatsType(type){
	var id = $('#id').val();
	window.location.href = '/#/log/cschart/?id=' + id + '&chartType='+ type.value;
}

function chooseChannelFollowState(state){
	var state = state.value
	var server = document.getElementById('follow-server').value
	var priority = document.getElementById('follow-priority').value
	var pagination = document.getElementById('follow-pagination').value
	window.location.href = '/#/log/channelstats/fe/?state='+state +'&server='+server+'&priority='+priority+ '&pagination='+pagination
}

function chooseChannelFollowServer(server){
	var server = server.value
	var state = document.getElementById('follow-state').value
	var priority = document.getElementById('follow-priority').value
	var pagination = document.getElementById('follow-pagination').value
	window.location.href = '/#/log/channelstats/fe/?state='+state +'&server='+server+'&priority='+priority+ '&pagination='+pagination
}

function chooseChannelFollowPriority(priority){
	var priority = priority.value
	var server = document.getElementById('follow-server').value
	var state = document.getElementById('follow-state').value
	var pagination = document.getElementById('follow-pagination').value
	window.location.href = '/#/log/channelstats/fe/?state='+state +'&server='+server+'&priority='+priority+ '&pagination='+pagination
}

function chooseChannelFollowPagination(pagination){
	var pagination = pagination.value
	var server = document.getElementById('follow-server').value
	var state = document.getElementById('follow-state').value
	var priority = document.getElementById('follow-priority').value
	window.location.href = '/#/log/channelstats/fe/?state='+state +'&server='+server+'&priority='+priority+ '&pagination='+pagination
}

function updateFollowPriority(id){
	var priority = document.getElementById(id).value
	jQuery.get("/log/channelstats/fe/update/", { id: id,priority:priority });
}

function chooseFailureType(type)
{
	var url;
	if (type.value==0){
		ajaxUpdate('top_form','/graph/chart/blank');
		url='/graph/postfailurelist/all'
	}
	else if (type.value==1){
		ajaxUpdate('top_form','/graph/postfailurelist/channel/topform');
		channel=document.getElementById('channel_failure_value').value
		url='/graph/postfailurelist/channel?channel='+channel
	}
	else if (type.value==2){
		ajaxUpdate('top_form','/graph/postfailurelist/article/topform');
		article=document.getElementById('article_failure_value').value
		if (article==''){
			url='/graph/postfailurelist/channel?channel='
		}
		else {
			url='/graph/postfailurelist/article?article='+article
		}		
	}
	else if (type.value==3){
		ajaxUpdate('top_form','/graph/postfailurelist/feed/topform');
		feed=document.getElementById('feed_failure_value').value
		if (feed==''){
			url='/graph/postfailurelist/channel?channel='
		}
		else {
			url='/graph/postfailurelist/feed?feed='+feed
		}		
	}
	else if (type.value==4){
		ajaxUpdate('top_form','/graph/postfailurelist/campaign/topform');
		campaign=document.getElementById('campaign_failure_value').value
		if (campaign==''){
			url='/graph/postfailurelist/channel?channel='
		}
		else {
			url='/graph/postfailurelist/campaign?campaign='+campaign
		}		
	}
	
	else if (type.value==5){
		ajaxUpdate('top_form','/graph/postfailurelist/fchannel/topform');
		fchannel=document.getElementById('fchannel_failure_value').value
		if (fchannel==''){
			url='/graph/postfailurelist/channel?channel='
		}
		else {
			url='/graph/postfailurelist/fchannel?fchannel='+fchannel
		}		
	}

	ajaxUpdate('his_detail',url);
	document.getElementById('his_detail_url').value=url
}

function chooseDashboardRankingDetailTypePage(post_path,page)
{
	var url=post_path+'&page='+page;
	ajaxUpdate('his_detail_home',url);
}

function chooseDashboardRankingDetailTypeCertainPage(post_path)
{
	var page=document.getElementById('id_goToPages').value;
	var url=post_path+'&page='+page;
	ajaxUpdate('his_detail_home',url);
}

function chooseSourceChannel(account)
{
    id = account.value
	jQuery.getJSON("/fe/follow/account/ispay/", { id: id },
		  function(data){
		    result = data.result
		    if (result=='pay'){
		       document.getElementById('payed_info').style.display="";
		       document.getElementById('pay_info').style.display="";
		       document.getElementById('white_info').style.display="none";
		       document.getElementById('current_follower').innerHTML=data.currentCount
		       document.getElementById('usable_follower').innerHTML=data.usableCount
		       document.getElementById('assign_more_info').innerHTML="more"
		    }
		    else if (result=='free'){
		       document.getElementById('payed_info').style.display="none";
		       document.getElementById('pay_info').style.display="";
		       document.getElementById('white_info').style.display="none";
		       document.getElementById('assign_more_info').innerHTML=""
		    }
		    else if (result=='white'){
		       document.getElementById('payed_info').style.display="none";
		       document.getElementById('pay_info').style.display="none";
		       document.getElementById('white_info').style.display="";
		    }
		  });
    
}


function chooseChannalDetailType(type)
{
	document.getElementById('detail_type').value=type.value;
	ajaxUpdateChannelDetailType(type.value);
}


function retryChannelDetailType()
{
	value=document.getElementById('detail_type').value;
	ajaxUpdateChannelDetailType(value);
}

function submitFollowRule()
{
	$.facebox.loading();
	var form = $('form').each(function(){
		var str = $(this).serialize();
		jQuery.ajax({
			url: "/fe/follow/account/create/?type=safe",
			data: str,
			type: "POST",
			timeout:GLOBAL_TIMEOUT,
			success: function(data, textStatus){
				jQuery.facebox.close();
					if (data==''){
						// ajaxUpdate('ajax_content', ret_url);
						location.href = '#' + ret_url;
					}
					else{
						document.getElementById('ajax_content').innerHTML=data;
						pageRetrofit(jQuery('#ajax_content'));
						pageTracker._trackPageview(url);
						var scripts = document.getElementById('ajax_content').getElementsByTagName("script"); 
						for(var i=0;i<scripts.length;i++){ 
						    eval(scripts[i].innerHTML); 
						}
					}
			},
			error:function(xmlHttpRequest,error){
					jQuery.facebox.close();
					// ajaxUpdate('ajax_content', ret_url);
					location.href = '#' + ret_url;
			},
			complete:function(){
					}});
	})
	
}

function redirectTo(url)
{
	// ajaxUpdate('ajax_content', url);
	location.href = '#' + url;
	
}

function ajaxUpdateChannelDetailType(value)
{
	var id = document.getElementById('id').value
	var avatarUrl = document.getElementById('avatarUrl').value
	var url;
    if (value==0){
    	url='/chan/details/dm_inbox?id='+id+'&avatarUrl='+avatarUrl+'&type=0'
    }
	else if (value==1){
		url='/chan/details/dm_outbox?id='+id+'&avatarUrl='+avatarUrl+'&type=1'
	}
	else if (value==2){
		url='/chan/details/home_tweets?id='+id+'&avatarUrl='+avatarUrl+'&type=2'
	}
	else if (value==3){
		url='/chan/details/mentions?id='+id+'&avatarUrl='+avatarUrl+'&type=3'
	}
	else if (value==4){
		url='/chan/details/followers?id='+id+'&avatarUrl='+avatarUrl+'&type=4'
	}
	else if (value==5){
		url='/chan/details/friends?id='+id+'&avatarUrl='+avatarUrl+'&type=5'
	}
	else if (value==6){
		url='/chan/details/sent_tweets?id='+id+'&avatarUrl='+avatarUrl+'&type=6'
	}
	else if (value==7){
		url='/chan/details/retweets_by_others?id='+id+'&avatarUrl='+avatarUrl+'&type=7'
	}
	else if (value==8){
		url='/chan/details/retweets_by_you?id='+id+'&avatarUrl='+avatarUrl+'&type=8'
	}
	else if (value==9){
		url='/chan/details/your_tweets_retweeted?id='+id+'&avatarUrl='+avatarUrl+'&type=9'
	}
	else if (value==10){
		url='/chan/details/favorites?id='+id+'&avatarUrl='+avatarUrl+'&type=9'
	}
    ajaxUpdate('his_detail',url);
    document.getElementById('his_detail_url').value=url
    
	$('a[class*=facebox]').each(function(){
		$(this).click(function(){
			$('title').data('reloadOnSuccess',false);
			});
		});
}
function getPage(page,div)
{
	var url=document.getElementById('his_detail_url').value;
	var url_page;
	var has_param=url.indexOf("?")
	
	
	if (has_param==-1){
		url_page=url+'?page='+page
	}
	else {
		url_page=url+'&page='+page
	}	
	
	ajaxUpdate(div,url_page)
		
}

function changeConversationListPage(max_id,number)
{
	var url=document.getElementById('his_detail_url').value;
	var url_page;
	var has_param=url.indexOf("?");	
	
	if (has_param==-1){
		url_page=url+'?max_id='+max_id+'&div_number='+number;
	}
	else {
		url_page=url+'&max_id='+max_id+'&div_number='+number;
	}		
	if(number=='0'){
		ajaxUpdate("his_detail_0",url_page);
		tr_object=document.getElementById('conversation_more_tr_initial');
		document.getElementById("channel_table_id").deleteRow(tr_object.rowIndex);   
	}
	else{
		ajaxUpdate("his_detail_"+number,url_page);
		tr_object=document.getElementById('conversation_more_tr_'+number);
		document.getElementById("channel_table_id_"+number).deleteRow(tr_object.rowIndex); 
	}	
}

var CLASS_MODULE_MAP = {
    'FollowCampaign' : 'follow/account',
	'MCampaign' : 'post/rule/article',
	'FCampaign' : 'post/rule/feed',
	'CustomCampaign' : 'cust/rule',
	'MailCampaign' : 'email/campaign',
	'DMCampaign'      : 'dm/rule',
	'AdvancedDMCampaign' : 'dm/rule/advanced',
};

function getModuleName(obj_class_name){
	return CLASS_MODULE_MAP[obj_class_name]
}

function openNewWindow(url)
{
	window.open(url)
}


function toggleDetail(obj_class_name, obj_id){
	if (!document.getElementById('detail_'+obj_id).hasChildNodes()) {
		ajaxUpdate('detail_'+obj_id,'/'+getModuleName(obj_class_name)+'/detail/'+obj_id), 
		toggleDetailOld(obj_id)
	} else {
		toggleDetailOld(obj_id)
	}
}

function toggleDetailOld(obj_id){
	if (document.getElementById('img_show_'+obj_id).style.display=="none") {
		document.getElementById('img_show_'+obj_id).style.display="";
		document.getElementById('img_hide_'+obj_id).style.display="none";
		document.getElementById('detail_'+obj_id).style.display="none";
	} else { 
		document.getElementById('img_show_'+obj_id).style.display="none";
		document.getElementById('img_hide_'+obj_id).style.display="";
		document.getElementById('detail_'+obj_id).style.display="";
	}
}

function toggleAnalytics(check)
{
	if (check.checked) {
		document.getElementById('analytics_info').style.display="";
	}
	else {
		document.getElementById('analytics_info').style.display="none";
	}
}

function toggleRandomize(check)
{
	if (check.checked) {
		document.getElementById('randomize_time_count_info').style.display="";
	}
	else {
		document.getElementById('randomize_time_count_info').style.display="none";
	}
}

function toggleRandomizeSelect(selector){
	document.getElementById('randomize_time_count_value').value=selector.value;
}

function modifyRandomizeTimeCount(interval){
	var json = eval("("+document.getElementById('schedule_interval_json').innerHTML+")");
	var order = document.getElementById('schedule_interval_order').value.split('.');
	$("#randomize_time_count").empty();
	var selector = document.getElementById('randomize_time_count');	
	var tag = false;
	for(var i=0;i<order.length;i++){
		if(tag){
			break;
		}	
		if(order[i]==interval.value){
			tag = true;
		}
		var item = new Option(json[order[i]],order[i]);   
	    selector.options.add(item);   
	}
	var value = document.getElementById('randomize_time_count_value').value;
	var options = selector.options;
	selector.value=interval.value;
	for(var i=0;i<options.length;i++){
		if(options[i].value==value){
			selector.value=value;
		}
	}
}

function toggleCustom(check)
{
	if (check.checked) {
		document.getElementById('custom_form').style.display="";
		document.getElementById('choice_form').style.display="none";
	}
	else {
		document.getElementById('custom_form').style.display="none";
		document.getElementById('choice_form').style.display="";
	}
}

function toggleCampaign(check)
{
	if (check.checked) {
		document.getElementById('campaign_info').style.display="none";
	}
	else {
		document.getElementById('campaign_info').style.display="";
	}
}

function togglePromote(type){
	if (type.value==0) {
		document.getElementById('account-promote').style.display="";
	}
	else {
		document.getElementById('account-promote').style.display="none";
	}

}

function toggleCategory(type){
	if (type.value==0) {
		document.getElementById('nation-cat').style.display="";
		document.getElementById('city-cat').style.display="none";
	}
	else if(type.value==1){
		document.getElementById('city-cat').style.display="";
		document.getElementById('nation-cat').style.display="none";
	}

}

function toggleCityCat(type){
	if (type.value==1) {
		document.getElementById('city-category').style.display="";
	}
	else if(type.value==2){
		document.getElementById('city-category').style.display="none";
	}

}


function showSettingDetail(div){
	if (document.getElementById('setting_detail').style.display=="none") {
		document.getElementById('setting_detail').style.display=""
		document.getElementById('setting_info').innerHTML="Less<<"
	}
	else  {
		document.getElementById('setting_detail').style.display="none"
		document.getElementById('setting_info').innerHTML="More>>"
	}
	
}

function showReferrerDetail(){
	if (document.getElementById('referrer_detail').style.display=="none") {
		document.getElementById('referrer_detail').style.display=""
		document.getElementById('referrer_info').innerHTML="Less>>"
	}
	else  {
		document.getElementById('referrer_detail').style.display="none"
		document.getElementById('referrer_info').innerHTML="More>>"
	}
	
}

var USER_STATE_MAP = {
	    0 : 'unapproved',
		1 : 'standard',
		2 : 'unlimited',
		3 : 'admin'
	}
	
function toggleUserCmpStatus(mail)
{	
	jQuery.get("/api/usr/admin/?op=toggle_cmp_status", { mail: mail });
}

function upUserState(mail)
{	
	jQuery.post("/api/usr/upgrade/", { mail: mail },
			  function(data){
			    document.getElementById('state_email_'+mail).innerHTML=USER_STATE_MAP[data]
			  });
}


function downUserState(mail)
{
	jQuery.post("/api/usr/degrade/", { mail: mail },
			  function(data){
			    document.getElementById('state_email_'+mail).innerHTML=USER_STATE_MAP[data]
			  });
}

function setUserState(self, mail) {
	jQuery.post("/api/usr/upgrade/", 
		{ mail: mail, value: self.options[self.selectedIndex].value - 1 });		
}

function changeSkipFlag()
{
    var flag=document.getElementById('skipflag').innerHTML
	jQuery.getJSON("/fe/follow/account/whitelist/skip/", { flag: flag },
			  function(data){
			    result = data.result
			    document.getElementById('skipflag').innerHTML=result
			  });
}

function changeGroupStatus(id,name,chid)
{
    if (document.getElementById('add_'+id).style.display=='none'){
       action = 'Exclude'
    }
    else if (document.getElementById('minus_'+id).style.display=='none'){
       action = 'Include'
    }
    jQuery.getJSON("/chan/facebook/group/change/", { action: action,id : id,name:name, chid: chid},
			  function(data){
			    result = data.result
			    show = document.getElementById('showHidden')
			    if (result=='Included'){
			       document.getElementById('add_'+id).style.display='none'
			       document.getElementById('minus_'+id).style.display=''
			       document.getElementById('status_'+id).innerHTML=result
			    }
			    else if (result=='Excluded'){
			       if (show.checked){
			       document.getElementById('add_'+id).style.display=''
			       document.getElementById('minus_'+id).style.display='none'
			       document.getElementById('status_'+id).innerHTML=result
			       }
			       else {
			       document.getElementById('list_tr_id_'+id).style.display='none'
			       }
			    }
			  });
}

function changePageStatus(id,name,chid)
{
    if (document.getElementById('add_'+id).style.display=='none'){
       action = 'Exclude'
    }
    else if (document.getElementById('minus_'+id).style.display=='none'){
       action = 'Include'
    }
    jQuery.getJSON("/chan/facebook/page/change/", { action: action,id : id,name:name, chid: chid},
			  function(data){
			    result = data.result
			    show = document.getElementById('showHidden')
			    if (result=='Included'){
			       document.getElementById('add_'+id).style.display='none'
			       document.getElementById('minus_'+id).style.display=''
			       document.getElementById('status_'+id).innerHTML=result
			    }
			    else if (result=='Excluded'){
			       if (show.checked){
			       document.getElementById('add_'+id).style.display=''
			       document.getElementById('minus_'+id).style.display='none'
			       document.getElementById('status_'+id).innerHTML=result
			       }
			       else{
			       document.getElementById('list_tr_id_'+id).style.display='none'
			       }
			    }
			  });
}


function changeCurrentUser(mail)
{
	if(mail==''){
		jQuery.post('/api/usr/changeuser', null,function(data){
			data = data.substring(1, data.length - 1);
			var userName = data.split("|")[0];
			changeHeaderUserUI(userName);
			$('#button-clear-proxy').hide();
		});	
	}
	else{
		loading_start();
		jQuery.post('/api/usr/changeuser/?mail='+mail, null,function(data){
			if(data){
				data = data.substring(1, data.length - 1);
				var userName = data.split("|")[0];
				var useProxy = data.split("|")[1];
				changeHeaderUserUI(userName);
				if (useProxy == "True")
					$('#button-clear-proxy').show();
			}else{
				changeHeaderUserUI(mail);
			}
			
		},'html');	
	}
}

function changeHeaderUserUI(account){
	document.getElementById("account_board").innerHTML = "<strong>"+account+"</strong>"
	loading_complete();
}

function updateFChannelAll() 
{ 
	var html5=displayHtml5Define();
	updateFChannelHisDetail(html5); 
    updateFChannelInfo(getInfoType(),false,html5); 
} 

function updateFChannelHisDetail() 
{ 
	var html5=displayHtml5Define();
    var fchannel = document.getElementById('fchannel').value 
    var fchannelCompare = document.getElementById('fchannel_compare').value 
    if(html5){
        ajaxUpdate('his_detail','/graph/fchannel/chart/detail/html5',{fchannel: fchannel, fchannelCompare:fchannelCompare, timeRange: getTimeRange()}) 
    }
    else{
        ajaxUpdate('his_detail','/graph/fchannel/chart/detail',{fchannel: fchannel, fchannelCompare:fchannelCompare, timeRange: getTimeRange()}) 
    }
} 
 
function updateFChannelHisDetailT(timeRange,html5) 
{ 
    toggleTimeRangeDisplay(timeRange); 
    updateFChannelHisDetail(); 
} 

function showPic() 
{ 
 	   url = document.getElementById('fbPicture').value 
 	   jQuery.facebox(imagePage(url)) 
} 

function imagePage(url) 
{ 
   return "<img src='"+url+"'>" 
} 

function changeTwitterInfo(channel) 
{ 
} 

function changeFacebookInfo(channel) 
{ 
  if (channel.value==""){ 
     document.getElementById('f_info').style.display="none"; 
   } 
   else { 
     document.getElementById('f_info').style.display=""; 
   } 
} 

function changeDivDisplay(form ,id) 
{ 
   if (form.value==""){ 
     document.getElementById(id).style.display="none"; 
   } 
   else { 
     document.getElementById(id).style.display=""; 
   } 
} 


function showUpgradeInfo()
{
}

var sns = {
          
    rule : {
        onScheduleTypeChange : function(element){
            if (element.value==0){
                document.getElementById('interval_id').style.display="none";
                document.getElementById('start_id').style.display="none";
                document.getElementById('end_id').style.display="none";
                document.getElementById('randomize_info').style.display="none";
                document.getElementById('randomize_checkbox').checked=false;
                $("#randomize_time_count").empty();
            } else if(element.value==1){
                document.getElementById('interval_id').style.display="none";
                document.getElementById('start_id').style.display="";
                document.getElementById('end_id').style.display="none";
                document.getElementById('randomize_info').style.display="none";
                document.getElementById('randomize_checkbox').checked=false;
                $("#randomize_time_count").empty();
            } else if(element.value==2){
                document.getElementById('interval_id').style.display="";
                document.getElementById('start_id').style.display="";
                document.getElementById('end_id').style.display="";
                document.getElementById('randomize_info').style.display="";
                modifyRandomizeTimeCount(document.getElementById('schedule_interval'));
            }
        },
        
        activation : function(obj_class_name, obj_id){
        	// alert(obj_class_name);
            if (document.getElementById('img_activate_'+obj_id).style.display=="none") {
                deactiveRule(obj_class_name, obj_id)
            } else { 
                if(obj_class_name=='MCampaign' || obj_class_name=='FCampaign'){
                	jQuery.getJSON("/post/rule/check/",{ id: obj_id}, function(json){
                        result=json.result
                        if (result=='channel'){
                           jQuery.facebox(errorPage('noChannel'));
                        }
                        else if (result=='content'){
                           jQuery.facebox(errorPage('noContent'));
                        }
                        else{
                           activeRule(obj_class_name, obj_id)
                        }
                    });
                }else{
                    activeRule(obj_class_name, obj_id)
                }
            }
        }
        

    }
}

function activeRule(obj_class_name, obj_id){
    document.getElementById('img_activate_'+obj_id).style.display="none";
    document.getElementById('img_deactivate_'+obj_id).style.display="";
    document.getElementById('status_'+obj_id).innerHTML="Active";
    detailElement = document.getElementById('detail_'+obj_id)
    if (detailElement && detailElement.hasChildNodes()){
    	document.getElementById('detail_'+obj_id).innerHTML="";
        document.getElementById('detail_'+obj_id).style.display="none";
		document.getElementById('img_hide_'+obj_id).style.display="none";
		document.getElementById('img_show_'+obj_id).style.display="";
    }
    jQuery.get('/'+getModuleName(obj_class_name)+'/activate/?id='+obj_id);
}

function deactiveRule(obj_class_name, obj_id){
    document.getElementById('img_activate_'+obj_id).style.display="";
    document.getElementById('img_deactivate_'+obj_id).style.display="none";
    document.getElementById('status_'+obj_id).innerHTML="Inactive";
    detailElement = document.getElementById('detail_'+obj_id)
    if (detailElement && detailElement.hasChildNodes()){
    	document.getElementById('detail_'+obj_id).innerHTML="";
        document.getElementById('detail_'+obj_id).style.display="none";
		document.getElementById('img_hide_'+obj_id).style.display="none";
		document.getElementById('img_show_'+obj_id).style.display="";
    }
    jQuery.get('/'+getModuleName(obj_class_name)+'/deactivate/?id='+obj_id);
}

function msgLengthCount(jmsg, jurl, jfb) {
    delta_url = 0;
    if (jurl&&(jurl.value.length>0)){
        delta_url = SHORT_URL_LENGTH;
    }
    delta_fb = 0;
    if (jfb&&jfb.checked){
        delta_fb = 4;
    }
    return jmsg.value.length + delta_url + delta_fb;
}

function getAffixesSymbol(id){
	if(id.indexOf('parenthesis')!=-1){
		return '()';
	}
	else if(id.indexOf('bracket')!=-1){
		return '[]';
	}
	else if(id.indexOf('brace')!=-1){
		return '{}';
	}
	else if(id.indexOf('hyphen')!=-1){
		return '-';
	}
	else if(id.indexOf('colon')!=-1){
		return ':';
	}
	else if(id.indexOf('underscore')!=-1){
		return '_';
	}
	else{
		return document.getElementById(id).value;
	}
}

function affixesCheck(checked,id,affixes_element){
	var affix=getAffixesSymbol(id);	
	var affixes=affixes_element.value;
	
	if(checked){
		if(affixes){		
			affixes=affixes+'SubstituteSymbol'+affix;
		}
		else{
			affixes=affix;
		}
		affixes_element.value=affixes;
	}
	else{
		affixes_list=affixes.split('SubstituteSymbol');
		affixes='';
		for(var i=0;i<affixes_list.length;i++){
			if(affixes_list[i]!=affix){
				if(affixes==''){
					affixes=affixes_list[i];
				}
				else{
					affixes=affixes+'SubstituteSymbol'+affixes_list[i];
				}
			}
		}
		affixes_element.value=affixes;
	}
}


function checkAffixesDuplicate(type,symbol,affixes_element){
	var tag=true;
	var affixes=affixes_element.value;
	if(symbol=='-'||symbol=='_'||symbol==':'){
		if(affixes.indexOf(symbol)!=-1){
			tag=false;
			document.getElementById(type+'_title_input_error_duplicate').style.display='';
		}
	}
	return tag;
}

function prefixesCheck(check){
	var checked=check.checked;
	var id=check.id;
	var prefixes_element=document.getElementById('prefixDelimter');
	affixesCheck(checked,id,prefixes_element);
}

function suffixesCheck(check){
	var checked=check.checked;
	var id=check.id;
	var suffixes_element=document.getElementById('suffixDelimter');
	affixesCheck(checked,id,suffixes_element);
}

function addPrefixesInput(check){
	var checked=check.checked;
	if(checked){
		document.getElementById('prefix_title_input_label').style.display='none';
		document.getElementById('prefix_title_input_info').style.display='';
	}
	else{
		document.getElementById('prefix_title_input_label').style.display='';
		document.getElementById('prefix_title_input_info').style.display='none';
		var prefixes_element=document.getElementById('prefixDelimter');
		if(checkAffixesDuplicate('prefix',document.getElementById('prefix_title_input').value,prefixes_element)){
			affixesCheck(checked,'prefix_title_input',prefixes_element);		
		}
	}	
}

function addSuffixesInput(check){
	var checked=check.checked;
	if(checked){
		document.getElementById('suffix_title_input_label').style.display='none';
		document.getElementById('suffix_title_input_info').style.display='';
	}
	else{
		document.getElementById('suffix_title_input_label').style.display='';
		document.getElementById('suffix_title_input_info').style.display='none';
		var suffixes_element=document.getElementById('suffixDelimter');
		if(checkAffixesDuplicate('suffix',document.getElementById('suffix_title_input').value,suffixes_element)){
			affixesCheck(checked,'suffix_title_input',suffixes_element);
		}
	}	
}

function intialAffixes(affix,type){
	var tag=true;
	if(affix!=''){	
		if(affix.indexOf("u'")!=-1){		
			affix=affix.split("'")[1];
		}
		if(affix==''){
			tag=false;
		}
		var affixes_list=new Array();
		affixes_list=affix.split('SubstituteSymbol');
		if(tag){
			for(var i=0;i<affixes_list.length;i++){
				var id='';
				if(affixes_list[i]=="()"){
					id=type+'_title_parenthesis';
				}
				else if(affixes_list[i]=="[]"){
					id=type+'_title_bracket';
				}
				else if(affixes_list[i]=="{}"){
					id=type+'_title_brace';
				}
				else if(affixes_list[i]=="-"){
					id=type+'_title_hyphen';
				}
				else if(affixes_list[i]==":"){
					id=type+'_title_colon';
				}
				else if(affixes_list[i]=="_"){
					id=type+'_title_underscore';
				}
				else{
					id=type+'_title_input_check';
					document.getElementById(type+'_title_input').value=affixes_list[i];
					document.getElementById(type+'_title_input_label').style.display='none';
					document.getElementById(type+'_title_input_info').style.display='';		
					document.getElementById(type+'_title_input_hidden').value=affixes_list[i];				
				}
				document.getElementById(id).checked=true;
			}
		}
	}
	else{tag=false;}
	if(!tag){
			document.getElementById(type+'_title_parenthesis').checked=true;
			document.getElementById(type+'_title_hyphen').checked=true;
			if(type=='prefix'){
				prefixesCheck(document.getElementById('prefix_title_parenthesis'));
				prefixesCheck(document.getElementById('prefix_title_hyphen'));
			}
			else{
				suffixesCheck(document.getElementById('suffix_title_parenthesis'));
				suffixesCheck(document.getElementById('suffix_title_hyphen'));
			}	
	}

}

function prefixTitleCheck(check){
	var checked=check.checked;
	if(checked){
		prefixes=document.getElementById('prefixDelimter').value;
		intialAffixes(prefixes,'prefix');	
		document.getElementById('prefix_title_detail').style.display='';		
	}
	else{
		document.getElementById('prefix_title_detail').style.display='none';
	}
}

function suffixTitleCheck(check){
	checked=check.checked;
	if(checked){
		suffixes=document.getElementById('suffixDelimter').value;
		intialAffixes(suffixes,'suffix');	
		document.getElementById('suffix_title_detail').style.display='';		
	}
	else{
		document.getElementById('suffix_title_detail').style.display='none';
	}
}


function addNewShortLink(media_url){
	var number=parseInt(document.getElementById('current_link_number').value);
	var tag=true;
	if(document.getElementById('verify_error_add_new_number_'+String(number))!=null){
		document.getElementById('verify_error_add_new_number_'+String(number)).style.display='none';
		document.getElementById('verify_error_blank_number_'+String(number)).style.display='none';
		document.getElementById('verify_error_invalid_number_'+String(number)).style.display='none';
		if(document.getElementById('checked_link_number_'+String(number)).style.display!=''){
			document.getElementById('verify_error_add_new_number_'+String(number)).style.display='';	
			tag=false;	
		}	}
	if(tag){
		var newNode=document.createElement("div");   
	    newNode.setAttribute("id","short_link_number_"+String(number+1));   
	    newNode.style.paddingBottom='5px';
		
		document.getElementById("custom_rule_form").insertBefore(newNode,document.getElementById("short_link_add_cursor"));   	
		
		var div_string="<div style='padding-top:5px;'><div class='fieldLabel' style='width: 65px;text-align:right;'><strong>Link:</strong></div>"
							+"<div class='fieldInput'><span id='verify_link_input_number_"+String(number+1)+"' style='display:-moz-inline-box;display:inline-block;width:310px;'><input type='text' id='short_link_url_number_"+String(number+1)+"' size='45'/></span>"
							+"<span id='verify_link_number_"+String(number+1)+"'>&nbsp;<a class='cursorPointer' href='javascript:void(0);' onclick='verifyLinkCustom("+String(number+1)+",\""+media_url+"\")'title='Verify this link'>"
						    +"<img src='"+media_url+"sns/images/check.png' border='0' class='cursorPointer img' alt='Verify this link'/></a>&nbsp;</span>"
						    +"<span id='checked_link_number_"+String(number+1)+"' style='display:none'>&nbsp;<a href='javascript:void(0);' onclick='' title='Link verified'>"
						    +"<img src='"+media_url+"sns/images/link_check.png' border='0' class='cursorPointer img' alt='Link verified'/></a></span>"
						    +"<span id='delete_link_number_"+String(number+1)+"' style='display:none'><a class='cursorPointer' href='javascript:void(0);' onclick='deleteCurrentShortLink("+String(number+1)+",\""+media_url+"\")' title='Delete'>"
						    +"<img src='"+media_url+"sns/images/link_delete.png' border='0' class='cursorPointer img' alt='Delete'/></a></span>"
						    +"<span id='add_link_number_"+String(number+1)+"' style='display:none'><a class='cursorPointer' href='javascript:void(0);' onclick=\"addNewShortLink('"+media_url+"')\" title='Add more link'>"						    
						    +"<img src='"+media_url+"sns/images/link_add.png' border='0' class='cursorPointer img' alt='Add more link'/></a></span>"
						    +"<span><label id='verify_error_blank_number_"+String(number+1)+"' style='display:none' class='errorlist'>Need a link</label>"
						    +"<span><label id='verify_error_invalid_number_"+String(number+1)+"' style='display:none' class='errorlist'>Invalid link</label></span>"
						    +"<span><label id='verify_error_add_new_number_"+String(number+1)+"' style='display:none' class='errorlist'>Verify this link before you add a new one</label></div></div>"			        
						    +"<div class='clearFloat'></div>"					    
							+"<div id='title_div_number_"+String(number+1)+"' style='display:none'><div class='fieldLabel' style='width:65px;text-align:right;'><strong>Title:</strong></div>"
							+"<div class='fieldInput'><input type='text' id='short_link_title_number_"+String(number+1)+"' size='40'/></div></div>"
						    +"<div class='clearFloat'></div></div>";
		var slice="<div id='slice_div_number_"+String(number+1)+"' class='formSliceShort'></div>";
		newNode.innerHTML=div_string;

		var total=0;
		var lastNode_number;
		for(var i=1;i<=number;i++){
			if(document.getElementById('short_link_number_'+String(i))!=null){
				total+=1;
				lastNode_number=i;
			}
		}
		if(lastNode_number){
			document.getElementById('add_link_number_'+String(lastNode_number)).style.display='none';		
		}
		if(total!=0){
			newSliceNode=document.createElement("div"); 
			newSliceNode.setAttribute("id","slice_div_number_"+String(number+1));   
			document.getElementById("custom_rule_form").insertBefore(newSliceNode,newNode); 
			newSliceNode.className='formSliceShort';
		}
		document.getElementById('current_link_number').value=String(number+1);
	}
}

function deleteCurrentShortLink(number,media_url){
	var current=parseInt(document.getElementById('current_link_number').value);
	var total=0;
	var lastNode_number;
	var second_last_number;
	var firstNode_number;
	var second_first_number;	
	for(var i=1;i<=parseInt(current);i++){
		if(document.getElementById('short_link_number_'+String(i))!=null){
			total+=1;
			if(total==1){
				firstNode_number=i;
			}
			if(total==2){
				second_first_number=i;
			}
			if(lastNode_number){
				second_last_number=lastNode_number;
			}
			lastNode_number=i;
		}
	}	
	var parent=document.getElementById("custom_rule_form"); 
	var child=document.getElementById("short_link_number_"+String(number));
	parent.removeChild(child);
	if(number==firstNode_number){
		parent.removeChild(document.getElementById('slice_div_number_'+String(second_first_number)));
	}
	else{
		parent.removeChild(document.getElementById('slice_div_number_'+String(number)));
	}
	if(total==1){
		addNewShortLink(media_url);
	}
}

function deleteCurrentShortLinkUpdate(number,exist,media_url){
	document.getElementById("short_link_number_"+String(number)).style.display='none';
	var to_be_deleted=document.getElementById('links_to_be_deleted');
	var delete_string=to_be_deleted.value;
	if(delete_string!=''){
		delete_string=delete_string+'SubstituteLink'+document.getElementById('short_link_id_number_'+String(number)).value;
	}
	else{
		delete_string=document.getElementById('short_link_id_number_'+String(number)).value;
	}
	to_be_deleted.value=delete_string;
	var delete_list=delete_string.split('SubstituteLink');
	if(delete_list.length==exist){
		var current=parseInt(document.getElementById('current_link_number').value);
		var total=0;
		for(var i=exist+1;i<=parseInt(current);i++){
			if(document.getElementById('short_link_number_'+String(i))!=null){
				total+=1;
			}
		}
		if(total==0){
			addNewShortLink(media_url);
		}
	}
	
	var current=parseInt(document.getElementById('current_link_number').value);
	var total=0;
	var lastNode_number;
	var second_last_number;
	var firstNode_number;
	var second_first_number;
	for(var i=1;i<=parseInt(current);i++){
		if(document.getElementById('short_link_number_'+String(i))!=null){
			total+=1;
			if(total==1){
				firstNode_number=i;
			}
			if(total==2){
				second_first_number=i;
			}
			if(lastNode_number){
				second_last_number=lastNode_number;
			}
			lastNode_number=i;
		}
	}	
	var parent=document.getElementById("custom_rule_form"); 
	if(number==firstNode_number){
		parent.removeChild(document.getElementById('slice_div_number_'+String(second_first_number)));
	}
	else{
		parent.removeChild(document.getElementById('slice_div_number_'+String(number)));
	}
}

function getShortLinks(start_number,string_id,type){
	var number=parseInt(document.getElementById('current_link_number').value);
	var links_string='';
	for(var i=start_number+1;i<=number;i++){
		if(document.getElementById('short_link_number_'+String(i))!=null){
			var url=document.getElementById('short_link_url_number_'+String(i)).value;
			var title=document.getElementById('short_link_title_number_'+String(i)).value;
			if(url!='' && document.getElementById('checked_link_number_'+String(i)).style.display==''){
				if(links_string==''){
					links_string=url;
				}
				else{
					links_string=links_string+'SubstituteLink'+url;
				}
				links_string=links_string+'SubstituteInsideLink'+title;				
			}
		}
	}
	document.getElementById(string_id).value=links_string;
	if(type=='update'){
		var delete_string=document.getElementById('links_to_be_deleted').value;
		var links_exist='';
		for(var j=1;j<=start_number;j++){
			var id=document.getElementById('short_link_id_number_'+String(j)).value;
			if(id){			
				if(delete_string.indexOf('id')==-1){
					if(links_exist==''){
						links_exist=id;
					}
					else{
						links_exist=links_exist+'SubstituteLink'+id;
					}
					links_exist=links_exist+'SubstituteInsideLink'+document.getElementById('short_link_title_number_'+String(j)).value;
				}		
			}	
		}
		document.getElementById('links_string').value=links_exist;
	}
	return checkShortLinksSubmit(type,start_number);
}

function checkShortLinksSubmit(type,exist){
	document.getElementById('rule_name_error').style.display='none';
	document.getElementById('rule_link_error').style.display='none';
	var tag=true;
	if(document.getElementById('name_string').value==''){
		tag=false;
		document.getElementById('rule_name_error').style.display='';
	}
	if(type=='create'){
		if(document.getElementById('links_string').value==''){
			tag=false;
			document.getElementById('rule_link_error').style.display='';
		}
	}
	else if(type=='update'){
		var to_be_deleted=document.getElementById('links_to_be_deleted').value;
		if(to_be_deleted!=''){
			var delete_list=to_be_deleted.split('SubstituteLink');
			if(document.getElementById('links_to_be_created').value=='' && delete_list.length==exist){
				tag=false;
				document.getElementById('rule_link_error').style.display='';
			}
		}
	}
	return tag
}

/**
 * Perform one-time processing for each page load.
 */

jQuery(document).ready(function() {
	pageRetrofit(jQuery("body"));
});

/**
 * Retrofit certain generic DOM elements with JS behavior.
 * 
 * This must be called in an window.onload context, or after the window.onload
 * context is known to be valid.
 */

function pageRetrofit(context) {
	jQuery(".retro",context).each(function() {

		var subject = jQuery(this);

		// Retrofit this element so that a click on it will submit the closest
		// containing form. Note: the form must be
		// present at the time of retrofit, not at the time of click.

		if ( subject.is(".formsubmit") ) {
			makeFormAjaxSubmit(subject);
		}

		// Retrofit a counter
		// !!! These should be restructured as separate functions, identified
		// dynamically instead of through if/else

		else if ( subject.is(".counter") ) {
			var id_msg = subject.attr("rel_msg");
			var id_url = subject.attr("rel_url");
            var id_fb = subject.attr("rel_fb");
            var id_type = subject.attr("rel_type");
			var jmsg = document.getElementById('id_msg');
			var jurl = document.getElementById('id_url');
            var jfb = document.getElementById('id_fb');
            var is_facebook = document.getElementById('is_facebook');
			
			var f = function() {
				var is_facebook = $('option[value=1]','#id_type').attr('selected');
				var maxCount = 140;
				if(is_facebook){
					maxCount = 420;
				}
				
				var shortUrlLength = 0;
				if (id_url) {
					if (jurl.value.length > 0)
						shortUrlLength = SHORT_URL_LENGTH;
					}
				
				var curCount = jmsg.value.length;
				if ( curCount > (maxCount - shortUrlLength) ) {
					jmsg.value = jmsg.value.substring(0,maxCount - shortUrlLength);
					// !!! eventually, make a beep
				} else {
					subject.empty();
					subject.append(maxCount - msgLengthCount(jmsg, jurl, jfb));
				}

				if ( subject.hasClass("low") ^ ((maxCount - curCount) <= 30) ) {
					if ( (maxCount - curCount) <= 30 ){
						subject.addClass("low");
					}else{
						subject.removeClass("low");
					}							   
				}
			};
			
			var g = function(){
				var is_facebook = $('option[value=1]','#id_type').attr('selected');
				var maxCount = 140;
				if(is_facebook){
					maxCount = 420;
				}
			    subject.get(0).innerHTML = ("" + (maxCount - msgLengthCount(jmsg, jurl, jfb)));
			};
			
			if (id_msg) {
				var msg = jQuery("#" + id_msg);
				msg.keyup(f);
				msg.focus(f);
				msg.keydown(f);
				msg.blur(f);
			}
			
			if (id_url) {
				var url = jQuery("#" + id_url);
				url.keyup(function() {
				    g();
					f();
				});
				url.keyup(function() {
				    g();
					f();
				});
				url.focus(function() {
				    g();
					f();
				});
				url.keydown(function() {
				    g();
					f();
				});
				url.blur(function() {
				    g();
					f();
				});
			}
			
            if (id_fb) {
            	var fb = jQuery("#" + id_fb);
                fb.click(function() {
                    g();
                });
            }
		}
		
		else if ( subject.is(".linkDescriptionCounter") ) {
			var id_description = subject.attr("rel_description");
			var jdescription = document.getElementById('id_fbDescription');
			
			var f = function() {
				var maxCount = 500;
				
				var curCount = jdescription.value.length;
				if (curCount > maxCount) {
					jdescription.value = jdescription.value.substring(0,maxCount);
					// !!! eventually, make a beep
				} else {
					subject.empty();
					subject.append(maxCount - jdescription.value.length);
				}

				if ( subject.hasClass("low") ^ ((maxCount - curCount) <= 30) ) {
					if ( (maxCount - curCount) <= 30 ){
						subject.addClass("low");
					}else{
						subject.removeClass("low");
					}							   
				}
			};
			
			if (id_description) {
				var description = jQuery("#" + id_description);
				description.keyup(f);
				description.focus(f);
				description.keydown(f);
				description.blur(f);
			}
		}
		
		else if ( subject.is(".twitterCallbackCounter") ) {
			var id_tweet = subject.attr("rel_tweet");
			var jtweet = document.getElementById('tweet');
			
			var f = function() {
				var maxCount = 140;
				if(document.getElementById('is_facebook_post')!=null){
					maxCount = 420;
				}
				
				var curCount = jtweet.value.length;
				if (curCount > maxCount) {
					jtweet.value = jtweet.value.substring(0,maxCount);
					// !!! eventually, make a beep
				} else {
					subject.empty();
					subject.append(maxCount - jtweet.value.length);
				}

				if ( subject.hasClass("low") ^ ((maxCount - curCount) <= 30) ) {
					if ( (maxCount - curCount) <= 30 ){
						subject.addClass("low");
					}else{
						subject.removeClass("low");
					}							   
				}
			};
			
			if (id_tweet) {
				var tweet = jQuery("#" + id_tweet);
				tweet.keyup(f);
				tweet.focus(f);
				tweet.keydown(f);
				tweet.blur(f);
			}
		}
		
		
		else if ( subject.is(".loadReportChart") ) {
			chooseReportType(this);			
		}		
		
		else if ( subject.is(".loadFollowChart") ) {
			chooseFollowType(this);			
		}
		
		else if ( subject.is(".loadDMChart") ) {
			chooseDMChartType(this);			
		}

		else if ( subject.is(".loadRanking") )  {
			chooseRankingType(this.value,false,1000,'');
		}	
		
		else if ( subject.is(".loadHomeRanking") )  {
			chooseRankingType(this.value,false,5,'home');
		}
		
		else if ( subject.is(".loadHomeChart") )  {
			updateHomeHisDetail();
		}
		
		else if ( subject.is(".loadBotType") )  {
			chooseBotType(this.value,false);
		}
		
		else if (subject.is(".searchInput")) {
			var name=subject.attr("name");
		}
		
		else if ( subject.is(".analyticsCheck") ) {
			if (this.checked){				
				document.getElementById('analytics_info').style.display="";
			}
			else{
				document.getElementById('analytics_info').style.display="none";
			}
		}
		
		else if ( subject.is(".scheduleTypeCheck") ) {
			sns.rule.onScheduleTypeChange(this);
		}
		
		else if ( subject.is(".randomizeCheck") ) {
			if(this.style.display!='none'){
				if (this.checked){				
					document.getElementById('randomize_time_count_info').style.display="";
				}
				else{
					document.getElementById('randomize_time_count_info').style.display="none";
				}
			}
		}

		else if ( subject.is(".campaignCheck") ) {
			if (this.checked){				
				document.getElementById('campaign_info').style.display="none";
			}
			else{
				document.getElementById('campaign_info').style.display="";
			}
		}	
		
		else if (subject.is(".randomizeTimeCount")){
			if(document.getElementById('interval_id').style.display=='none'){
				document.getElementById('randomize_info').style.display=='none'
			}
			else{
				document.getElementById('randomize_info').style.display==''
			}
			modifyRandomizeTimeCount(this);		

			var value = document.getElementById('randomize_time_count_value').value;
			if(value){
				document.getElementById('randomize_time_count').value=value;
			}
		}
		
		else if ( subject.is(".hideTwitter") ) {
		}
		
		else if ( subject.is(".hideFacebook") ) {
		}
		
		else if (subject.is(".promoteCheck")){
			togglePromote(this)
		}
		
		else if (subject.is(".promoteCategory")){
			toggleCategory(this)
		}
		
		else if (subject.is(".promoteCityCat")){
			toggleCityCat(this)
		}
		
		else if ( subject.is(".fbPostStyle") ) {
			if(document.getElementById('link_detail').style.display!='none'){
				$('#id_pic_info_current').text(parseInt($('#id_fbPicture_current').val()));
				$('#id_pic_info_total').text(parseInt($('#id_fbPicture_total').val()));
				if($('#thumbnail').attr('checked')){
					$('#link_img').attr('src',$('#id_fbPicture').val());
				}
			}
		}
		
		else if ( subject.is(".postingRuleUrl") ) {
			shift_link(this);
		}
		
		else if ( subject.is(".updateCustomCampaignLoad") ) {
			loadCustomCampaignLinks(this);
		}
		
		else if ( subject.is(".detailCustomCampaignLoad") ) {
			loadCustomCampaignLinks(this);
		}
		
		else if ( subject.is(".prefixTitileLoad") ) {
			prefixTitleCheck(this);
		}	
		
		else if ( subject.is(".suffixTitileLoad") ) {
			suffixTitleCheck(this);
		}	
		
		else if ( subject.is(".loadChannelDetail") ) {
			var type = document.getElementById('detail_type').value
			this.value=type;
			chooseChannalDetailType(this)
		}	
		
		else if ( subject.is(".loadFailure") )  {
			chooseFailureType(this)
		}
		
		else if ( subject.is(".loadUserCount") )  {
			chooseUserCount(this)
		}
		
		else if ( subject.is(".loadFilterType") )  {
			choosefilterType(this)
		}
		
		else if ( subject.is(".loadUserDate") )  {
			chooseUserDate(this)
		}
		
		else if ( subject.is(".loadPaymentFollowerCountList") ) {
			this.value=0;
		}
		
		else if ( subject.is(".loadPaymentHistoryList") ) {
			choosePaymentHistoryType(this);
		}
		
		else if ( subject.is(".loadDifferentReportChart") ) {
			var url=document.getElementById('report_url').value;
			var params=document.getElementById('report_params').value;
		}
		
		else if ( subject.is(".smsMenu") ) {
			subject.mouseover(function() {
				jQuery(".smsMenuAvatar",this).addClass("over");
			});

			subject.mouseout(function() {
				jQuery(".smsMenuAvatar",this).removeClass("over");
			});

			subject.click(function() {
				jQuery(this).addClass("active");
				var container = jQuery(".smsMenuContainer",this);
				container.show(500,function() {
					// !!! This may belong outside?
					jQuery("body").one("click",function(event) {
						container.hide(500);
						event.stopPropagation();
					});
				});
			});

			// Retrofit SMS Menu elements

			jQuery(".smsMenuElement",subject).mouseover(function() {
				jQuery(this).addClass("over");
			});

			jQuery(".smsMenuElement",subject).mouseout(function() {
				jQuery(this).removeClass("over");
			});
		}

	});
}


function facebox_ajax_get(url){
	jQuery.facebox.loading();
    jQuery.ajax({
	url: url,
	type: "GET",
	timeout:GLOBAL_TIMEOUT,
	success: function(result, textStatus){
    	jQuery.facebox(result);
    },
	error:function(XMLHttpRequest, textStatus, errorThrown){
		jQuery.facebox(errorPage(textStatus));
	},
	complete:function(result, textStatus){
		pageTracker._trackPageview(url);
	}
	});
}

function dm_reply_facebox(id,uid,avatarUrl,type){
	url = '/chan/details/dm/reply?id='+id+"&avatarUrl="+avatarUrl+"&type="+type+"&uid="+uid
	facebox_ajax_get(url);
}

function tweet_reply_facebox(id,uid,avatarUrl,type,replyto,home_tweet){
	url = '/chan/details/tweets/reply?id='+id+"&avatarUrl="+avatarUrl+"&type="+type+"&uid="+uid+"&replyto="+replyto+"&home_tweet="+home_tweet
	facebox_ajax_get(url);
}

function dm_send_facebox(id,uid,avatarUrl,type,sendto){
	url = "";
	if(sendto==''){
		url = '/chan/details/dm/send?id='+id+"&avatarUrl="+avatarUrl+"&type="+type+"&uid="+uid;	
	} else{
		url = '/chan/details/dm/send?id='+id+"&avatarUrl="+avatarUrl+"&type="+type+"&uid="+uid+"&sendto="+sendto;
	}
	facebox_ajax_get(url);
}

function retweet_facebox(id,uid,avatarUrl,type,replyto,text,tweet_origin_channel,origin_tweet_id){
	url = '/chan/details/tweets/retweet?id='+id+"&avatarUrl="+avatarUrl+"&type="+type+"&uid="+uid+"&replyto="+replyto+"&text="+text+"&tweet_origin_channel="+tweet_origin_channel+'&origin_tweet_id='+origin_tweet_id;
	facebox_ajax_get(url);
}

function follow_him(id,uid,avatarUrl,type){
	jQuery.getJSON('/chan/details/friends/follow_him?id='+id+"&avatarUrl="+avatarUrl+"&type="+type+"&uid="+uid, function(data) { 
		ret_url=data.ret_url;
		if(ret_url==''){
			jQuery.facebox('<div class="content" color="red"><div class="cb1"><div class="fieldLabel">User "'+data.user_b+'" is already a friend of "'+data.user_a+'"!</div><div class="clearFloat"></div></div></div>') 
		}		
	})
}

function delete_dm(id,avatarUrl,uid,type){
	jQuery.get("/chan/details/dm/delete?id="+id+"&avatarUrl="+avatarUrl+"&uid="+uid+"&type="+type, function(data) {
		tr_object=document.getElementById('channel_tr_id_'+id);
		document.getElementById("channel_table_id").deleteRow(tr_object.rowIndex);      
	})
}

function delete_dm_more(id,avatarUrl,uid,type,div_id){
	jQuery.get("/chan/details/dm/delete?id="+id+"&avatarUrl="+avatarUrl+"&uid="+uid+"&type="+type, function(data) {
		tr_object=document.getElementById('channel_tr_id_'+id);
		document.getElementById("channel_table_id_"+div_id).deleteRow(tr_object.rowIndex);      
	})
}

function delete_tweet(id,avatarUrl,uid,type){
	jQuery.get("/chan/details/tweets/delete?id="+id+"&avatarUrl="+avatarUrl+"&uid="+uid+"&type="+type, function(data) {
		tr_object=document.getElementById('channel_tr_id_'+id);
		document.getElementById("channel_table_id").deleteRow(tr_object.rowIndex);      
	})
}

function delete_tweet_more(id,avatarUrl,uid,type,div_id){
	jQuery.get("/chan/details/tweets/delete?id="+id+"&avatarUrl="+avatarUrl+"&uid="+uid+"&type="+type, function(data) {
		tr_object=document.getElementById('channel_tr_id_'+id);
		document.getElementById("channel_table_id_"+div_id).deleteRow(tr_object.rowIndex);      
	})
}

function unfollower_friend(id,screen_name,avatarUrl,uid,type){
	jQuery.get("/chan/details/friends/unfollow_him?id="+screen_name+"&avatarUrl="+avatarUrl+"&uid="+uid+"&type="+type, function(data) {
		tr_object=document.getElementById('channel_tr_id_'+id);
		document.getElementById("channel_table_id").deleteRow(tr_object.rowIndex);      
	})
}

function un_favorite(id,avatarUrl,uid,type,media_url){
	jQuery.get("/chan/details/favorites/delete?id="+id+"&avatarUrl="+avatarUrl+"&uid="+uid+"&type="+type, function(data) {
		document.getElementById('favorite_'+id).innerHTML="<span id='favorite_"+id+"'><a id='favorite_link_"+id+"' class='cursorPointer' href='javascript:void(0);' onclick=\"twitter_favorite('"+id+"','"
		+avatarUrl+"','"+uid+"','"+type+"','"+media_url+"')\" title='Favorite the Tweet'><img id='favorite_img_"+id+"' src='"+media_url+"sns/images/favorite.png' alt='Favorite the Tweet' border='0'  /></a></span>";   
	})
}

function twitter_favorite(id,avatarUrl,uid,type,media_url){
	jQuery.get("/chan/details/favorites/create?id="+id+"&avatarUrl="+avatarUrl+"&uid="+uid+"&type="+type, function(data) {
		document.getElementById('favorite_'+id).innerHTML="<span id='favorite_"+id+"'><a id='favorite_link_"+id+"' class='cursorPointer' href='javascript:void(0);' onclick=\"un_favorite('"+id+"','"
		+avatarUrl+"','"+uid+"','"+type+"','"+media_url+"')\" title='Unfavorite the Tweet'><img id='favorite_img_"+id+"' src='"+media_url+"sns/images/un_favorite.png' alt='Unfavorite the Tweet' border='0'  /></a></span>";
	})
}


var mouseEnter_conversation_controlFlag = true;


function getErrorPage(error){
	
	return '\
			<div>\
		    <div class="fieldDetail">'+
			errorPage(error)
		    +'\
			</div>\
		    <div class="clearFloat"></div>\
		    <div class="fieldDetail"><a href="/chan/twitter/login"> Go to add a Twitter account</a></div>\
		    <div class="clearFloat"></div>\
			</div>'
			;
	
}

// generate the ajax submit error page
function errorPage(error){
	var message;
	if(error == "timeout"){
		message =  "Your request is timeout. Please retry!";
	} else if(error == "parsererror"){
		message =  "Some required data is missing!";
	} else if(error == "error"){
		message = "Could not connect to server! Please retry a few moment later.";
	} else if(error == "duplicate"){
		message = "You can only have one active follower-building campaign for each source account at the same time!";
	} else if(error == "noChannel"){
		message = "Could not activate this campaign! All marketing channels of this campaign are deleted.";
	} else if(error == "noContent"){
		message = "Could not activate this campaign! All marketing contents of this campaign are deleted.";
	} else if(error == "safelist"){
		message = "You can have at most 3 safe lists!";
	} else if(error == "invalidint"){
	    message = "Not a valid int"
	} else if(error == "404"){
	    message = "Http Error 404: Page Not Found."
	} else if (error == "wrongint"){
	    message = "Not a valid amount"
	} else if(error == "noquota"){
		message = "You have no follower credit left for your Twitter account!";
		return "<div class='errorlist'>" + message + "</div>"+"<a href='/payment'>Buy  Twitter followers</a>"
	} else {
		message = "Encountered unknown error. Please retry!"
	}
	return "<div class='errorlist'>" + message + "</div>";
}

function conversationChangeAcc(id,avatarUrl){
	sd = document.getElementById('detail_type');
	location.href ='/#/chan/details/?id='+id+'&avatarUrl='+avatarUrl+'&type='+sd.value;
	document.getElementById('conversation_submenu').style.display='none';
}

function payByPaypal(){
	var amount = document.getElementById('payment_gross_input').value;
	var followers = document.getElementById('payment_followers_input').value;
	var singleFee = document.getElementById('payment_singleFee_input').value;
	url='/payment/pay/?amount='+amount+'&followers='+followers+'&singleFee='+singleFee;
	return  window.location.href=url;	
}

function payByPal(){
	var amount = document.getElementById('sns_payment').value;
	url='/payment/sns/pay/?amount='+amount
	return  window.location.href=url;	
}


function payByPaypalPremiumSubscription(){
	var type=document.getElementById('payment_gross_input').value;
	url='/#/payment/premium/subscription/initial/?type='+type;
	jQuery.get('/payment/premium/subscription/initial/?type='+type, function(data) {
		var response=eval("("+data+")");
		if(response['state']=='Success'){
			return  window.location.href=response['url'];
		}
		else{
			jQuery.facebox(response['html']); 
		}		
	})
}

function getTotalFollowers(id,followersMap){
	return followersMap[id];	
}

function getPaymentFeeSingle(count,feeSingleList){
	if(5<=count&&count<=9){
		return feeSingleList['0'];
	}
	else if(10<=count&&count<=49){
		return feeSingleList['1'];
	}
	else if(50<=count&&count<=99){
		return feeSingleList['2'];
	}
	else{
		return feeSingleList['3'];
	}
}

function choosePaymentTotalFollowers(total){
	var followersMap=eval("("+document.getElementById('jsonStringFollowers').value+")");
	var feeSingleList=eval("("+document.getElementById('jsonStringFee').value+")");
	var value=total.value;
	var count=getTotalFollowers(value,followersMap);
	var singleFee=getPaymentFeeSingle(count,feeSingleList);
	var gross=(parseInt(count)*parseFloat(singleFee)).toFixed(2);
	amount=String(gross).split('.');
	decimal=amount[1];
	if(!decimal){
		decimal="00"
	}
	else{
		if(decimal.length==1){
		    decimal=decimal+"0"
		}
	}
	document.getElementById('payment_gross_input').value=gross;
	document.getElementById('payment_count_decimal').innerHTML=decimal;
	
	document.getElementById('payment_followers_input').value=count;
	document.getElementById('payment_singleFee_input').value=singleFee;
	document.getElementById('payment_singleFee').innerHTML=singleFee;
	document.getElementById('payment_count').innerHTML=amount[0];
}

function choosePaymentHistoryType(typePayment) 
{ 
	var type = typePayment.value; 
    ajaxUpdate('his_detail','/payment/history/hisdetail?type='+String(type)); 
} 

function makeFormAjaxSubmit(subject){
	subject.data("click",1);
	subject.click(function() {
		if (subject.data("click")==1){
		subject.data("click",0);	
		var form = jQuery(this).closest("form");
		$.facebox.loading();
		if ( form.length == 1 ) {
			var str = form.serialize();
			jQuery.ajax({
				url: form.attr("action"),
				data: str,
				type: "POST",
				timeout:GLOBAL_TIMEOUT,
				success: function(data, textStatus){
					if (data.indexOf("AjaxErrorInfo")!=-1){
                        msg = data.split("&nbsp;")[1];
                        msg_html = "<div class='errorlist'>" + msg + "</div>"
			            jQuery.facebox(msg_html);
			        }else if (data.indexOf("CapabilityDisabledError")!=-1){
            			var msg = data.split("&nbsp;")[1];
            			// var msg_html = "<div class='errorlist'>" + msg +
						// "</div>"
            			var msg_html = "<div><span>" + msg + "You can click this link to check latest status update from our cloud computing host Google App Engine.</span><span></div> <div><a target='_blank' href='http://groups.google.com/group/google-appengine-downtime-notify?hl=en'>http://groups.google.com/group/google-appengine-downtime-notify?hl=en</a></span></div>"
            			jQuery.facebox(msg_html);
	    			}else if (data.indexOf("faceboxControls")==-1){
						jQuery.facebox.close();
						
                        if(data.indexOf("channel_list_update")!=-1){
                        	var response=eval("("+data+")");
                        	var keywords = response['keywords']
                        	if(keywords.length==0){
                        	document.getElementById('channel_keywords_td_'+response['id']).style.display='none'
                        	}else{
                        	document.getElementById('channel_keywords_td_'+response['id']).style.display=''
                        	}
                        	
                        	document.getElementById('channel_list_keywords_td_'+response['id']).innerHTML="<span title='"
                        			+response['keywords']+"'>"
                        			+response['keywords']
                        			+"</span>";
                        }
                        else if(data.indexOf("article_list_update")!=-1){
                        	var response=eval("("+data+")");
                        	if(response['urlHash']){
                        		document.getElementById('follow_building_campaign_msg_td_'+response['id']).innerHTML=response['msg']
                        		    +"<span title='"+response['url']+"'>"
                                	+"<a href='/"+response['urlHash']+"'>"+response['shortUrl']+"</a>"
                                	+"</span>";
                        	}else{
                        		document.getElementById('follow_building_campaign_msg_td_'+response['id']).innerHTML=response['msg'];
                        	}
                        	document.getElementById('follow_building_campaign_url_td_'+response['id']).innerHTML="<span title='"
                        			+response['url']+"'>"
                        			+"<a href='"+response['url']+"'>"
                        			+response['url']
                        			+"</span>";
                        }
                        
                        else if(data.indexOf("feed_list_update")!=-1){
                        	var response=eval("("+data+")");
                        	document.getElementById('follow_building_campaign_name_td_'+response['id']).innerHTML="<span title='"
                        			+response['name']+"' id='"+response['id']+"' class='cursorPointer'>"
                        			+response['name']
                        			+"</span>";
              				$("#"+response['id']).editInPlace({ 
            	    			url: "/feed/edit/",
            	    			bg_over: "#DCDCDC"  
            				});
                        	var urlInfo = response['url']
                        	var url = urlInfo.split("***")[0]
                        	document.getElementById('follow_building_campaign_url_td_'+response['id']).innerHTML="<span title='"
                        			+url+"'>"
                        			+"<a href='"+url+"'>"
                        			+url
                        			+"</span>";
                        }
                        
                        else{
    						if(data.indexOf("channel_retweet")==-1&&data.indexOf("channel_home_tweet")==-1&&data.indexOf("channel_send_dm")==-1){
    							page_reload();
    						}
                        }
					}else{
						jQuery.facebox(data);	
					}
				},
				error:function(xmlHttpRequest,error){
					jQuery.facebox(errorPage(error));
						},
				complete:function(){}
				});
			}
			}
		});
	
}


function sortByKeyWord(){
	var url = document.getElementById('post_path').value;
	var directType = document.getElementById('id_direct_type').value;
	var paginate_by = document.getElementById('id_paginate_num').value;
	var sortby = document.getElementById('id_sortBy_type').value;
	url = url.substring(0,url.indexOf('sortby'));
	var action = '';
	if (url.indexOf('?') == url.length-1){
		action = url+'sortby='+sortby+'&directType='+directType+'&paginate_by='+paginate_by;
	}else{
		if (url.indexOf('&') == url.length-1){
			action = url+'sortby='+sortby+'&directType='+directType+'&paginate_by='+paginate_by;
		}
		else{
			action = url+'&sortby='+sortby+'&directType='+directType+'&paginate_by='+paginate_by;
		}
	}
	var query = document.getElementById('query');
	if(query){
		action = action + '&query='+query.value;
	}
	location.href = "#"+action;
}

function moveContacts(FromComboName,ToComboName){
	
	var   FromCombo=document.getElementById(FromComboName);   
	var   ToCombo=document.getElementById(ToComboName);   
	var   to_remove_counter=0;

	for   (var   i=0;i<FromCombo.options.length;i++)   
	{   
	if   (FromCombo.options[i].selected==true)   
	{   
	var   addtext=FromCombo.options[i].text;   
	var   addvalue=FromCombo.options[i].value;   
	ToCombo.options[ToCombo.options.length]=new   Option(addtext,addvalue);   
	FromCombo.options[i].selected=false;   
	++to_remove_counter;   
	}   
	else   
	{   
	FromCombo.options[i-to_remove_counter].selected=false;   
	FromCombo.options[i-to_remove_counter].text=FromCombo.options[i].text;   
	FromCombo.options[i-to_remove_counter].value=FromCombo.options[i].value;   
	}   
	}   
	    
	// now cleanup the last remaining options
	var   numToLeave=FromCombo.options.length-to_remove_counter;   
	for   (i=FromCombo.options.length-1;i>=numToLeave;i--)     
	{     
	FromCombo.options[i]=null;   
	}   
	
}

function delete_obj(id,ret_url,path){
	req_url = path+"delete/?id="+id+"&ret_url="+ret_url
	del_obj(id,ret_url,req_url)
}

function delete_batch_obj(id,batch,ret_url,path){
	req_url = path+"delete/?id="+id+"&batch="+batch+"&ret_url="+ret_url
	del_obj(id+':'+batch,ret_url,req_url)
}

function del_obj(id,ret_url,req_url){
	jQuery.get(req_url, function(data) {
	    if (data.indexOf("AjaxErrorInfo")!=-1){
            var msg = data.split("&nbsp;")[1];
            var msg_html = "<div class='errorlist'>" + msg + "</div>"
            jQuery.facebox(msg_html);
	    }
	    else if (data.indexOf("CapabilityDisabledError")!=-1){
            var msg = data.split("&nbsp;")[1];
            var msg_html = "<div><span>" + msg + "You can click this link to check latest status update from our cloud computing host Google App Engine.</span><span></div> <div><a target='_blank' href='http://groups.google.com/group/google-appengine-downtime-notify?hl=en'>http://groups.google.com/group/google-appengine-downtime-notify?hl=en</a></span></div>"
            jQuery.facebox(msg_html);
	    }
	    else if (data.indexOf("Exception")!=-1){
            var msg_html = "<div class='errorlist'>Failed to delete this item. Please try later.</div>"
            jQuery.facebox(msg_html);
	    }
	    else {	    	
	    	if(document.getElementById('total_items_number')!=null){
	    		var current_number=parseInt(document.getElementById('total_items_number').innerHTML)-1;
		    	document.getElementById('total_items_number').innerHTML = current_number;
	    	}	    	
	    	tr_object=document.getElementById('list_tr_id_'+id);
	    	document.getElementById("layout_table").deleteRow(tr_object.rowIndex);      
	    }
	})
}


function delete_white_list(object){
	jQuery.get("/fe/follow/account/whitelist/delete/?obj="+object, function(data) {
		if (data.indexOf("Exception")!=-1){
            var msg_html = "<div class='errorlist'>Failed to delete this item. Please try later.</div>"
            jQuery.facebox(msg_html);
	    }
	    else {
			tr_object=document.getElementById('white_list_'+object);
			document.getElementById("layout_table").deleteRow(tr_object.rowIndex);      
	    }     
	})
}

function delete_black_list(type,object){
	jQuery.get("/log/blacklist/"+type+"/delete?obj="+object, function(data) {
		if (data.indexOf("Exception")!=-1){
            var msg_html = "<div class='errorlist'>Failed to delete this item. Please try later.</div>"
            jQuery.facebox(msg_html);
	    }
	    else {
			tr_object=document.getElementById('black_list_'+object);
			document.getElementById("black_list_table").deleteRow(tr_object.rowIndex);      
	    }          
	})
}

function delete_agent_list(name){
	jQuery.get("/log/agent/delete?name="+name, function(data) {
		if (data.indexOf("Exception")!=-1){
            var msg_html = "<div class='errorlist'>Failed to delete this item. Please try later.</div>"
            jQuery.facebox(msg_html);
	    }
	    else {
			tr_object=document.getElementById('bot_agent_list_'+id);
			document.getElementById("layout_table").deleteRow(tr_object.rowIndex);      
	    }           
	})
}

function delete_user_blacklist(name){
    jQuery.post("/usr/blacklist/delete/?name="+name, function(data) {
		if (data.indexOf("Exception")!=-1){
            var msg_html = "<div class='errorlist'>Failed to delete this item. Please try later.</div>"
            jQuery.facebox(msg_html);
	    }
	    else {
	    	tr_object=document.getElementById('list_tr_id_'+name);
			document.getElementById("layout_table").deleteRow(tr_object.rowIndex);      
	    }       
	})
}

function channel_twitter_sync(id){ 
	jQuery.get('/chan/twitter/sync?id='+id, function(data) { 
    	var response=eval("("+data+")");                        	
        document.getElementById('channel_list_avatar_'+id).src=response['avatarUrl'];  
        document.getElementById('channel_list_name_'+id).innerHTML=response['screen_name'];  	
	})
}

function channel_facebook_sync(id){ 
	jQuery.getJSON('/chan/facebook/sync?id='+id, function(data) { 
        document.getElementById('channel_list_avatar_'+id).src=data.avatarUrl
        document.getElementById('channel_list_name_'+id).innerHTML=data.name
        document.getElementById('channel_list_name_'+id).href=data.link
	})
}

function channel_adminpage_sync(id){ 
	jQuery.getJSON('/chan/fbpage/sync/?id='+id, function(data) { 
        document.getElementById('channel_list_avatar_'+id).src=data.avatarUrl
        document.getElementById('channel_list_name_'+id).innerHTML=data.name
        document.getElementById('channel_list_name_'+id).href=data.link
	})
}

function channel_group_sync(id){ 
	jQuery.getJSON('/chan/groupmember/sync/?id='+id, function(data) { 
        document.getElementById('channel_list_avatar_'+id).src=data.avatarUrl
        document.getElementById('channel_list_name_'+id).innerHTML=data.name
        document.getElementById('channel_list_name_'+id).href=data.link
	})
}

function loadDemoUser()
{
    var mail = document.getElementById('demo_user').value
	jQuery.post("/usr/load/demo/", { mail: mail },
		  function(data){
		  jQuery.facebox.close();
		  changeHeaderUserUI(data)
		  });
}

function clearProxyUser()
{
    jQuery.post("/usr/clear/proxy/",
		  function(data){
		  jQuery.facebox.close();
		  changeHeaderUserUI(data)
		  });
}

function confirmDeactivePremiumSubscriptionPaymentProfile(id)
{
	jQuery.get("/payment/premium/subscription/profile/cancel/confirm?id="+id, function(data) {		
		jQuery.facebox(data);
	});
}
function deactivePremiumSubscriptionPaymentProfile(id)
{
	jQuery.get("/payment/premium/subscription/profile/cancel/?id="+id, function(data) {
		response=eval("("+data+")");
		if(response.status=="Failure"){
			jQuery.facebox('<div class="content" color="red"><div class="cb1"><div class="fieldLabel">Sorry. Premium subscription payment profile is failed to be canceled.</div><div class="clearFloat"></div></div></div>') 
		}
		else{			
			jQuery.facebox.close();
			actionField=document.getElementById('payment_premium_subscription_profile_cancel_'+id);
			actionField.innerHTML="";
			statusLabel=document.getElementById('payment_Premium_subscription_profile_status_'+id);
			statusLabel.innerHTML="Cancelled";
		}		
	})
}

function pageload(hash){
	var url = hash;
	if(!hash){
		location.href = '#/home/';
	}else{
		ajaxUpdate('ajax_content', url, null, 'GET');
	}
}

function loading_start(){
	$(document).scrollTop(0);
	$('#ajax_statebar').fadeIn('slow');
}

function loading_complete(){
	$('#ajax_statebar').fadeOut('slow');
}

function page_load(url){
    var index = url.indexOf('?')
	if(!url || url =='' || url =='/' || index == 0 || index == 1){
		url = '/home/'
	}
	url = url.replace(/^.*#/, '');
	ajaxUpdate('ajax_content', url, null, 'GET');
}

function page_reload(){
	var url = location.href;
	url = url.replace(/^.*#/, '');
	ajaxUpdate('ajax_content', url, null, 'GET');
}


function ajaxFormSubmit(ret_url, submit, current_location, type){
	loading_start();
	
	var form = $(submit).closest('form');
	
	var str = form.serialize();
	var url = form.attr('action');
	
	$.ajax({
		url: url,
		type: 'POST',
		data: str,
		timeout:GLOBAL_TIMEOUT,
		success: function(result, textStatus){	
			if(result.indexOf('success')== -1 ){		
				if(type=='custom_campaign'){
					if(result.indexOf('duplicate_custom_campaign')!= -1){
						document.getElementById('rule_name_error_duplicate').style.display='';
					}
				}	
				else{				
					document.getElementById('ajax_content').innerHTML=result;
					
					pageRetrofit(jQuery('#ajax_content'));
					pageTracker._trackPageview(url);
					var scripts = document.getElementById('ajax_content').getElementsByTagName("script"); 
					for(var i=0;i<scripts.length;i++){ 
					    eval(scripts[i].innerHTML); 
					}
				}
			}else{
				if(ret_url){
					location.href = "#"+ret_url;
				}
				
				if(result.indexOf('settings_name')!= -1 ){
					var response=eval('('+result+')');
					document.getElementById('account_board').innerHTML="<strong>"+response['settings_name']+"</strong>";
				}
			}
		
		},
		error:function(XMLHttpRequest, textStatus, errorThrown){
		
		 
		},
		complete:function(result, textStatus){
			loading_complete();
			if(type=='feed_quick'){
				var location = window.location;
				if(current_location==location){
					if(document.getElementById('quick_post_feed_button')!=undefined){
						document.getElementById('quick_post_feed_button').disabled = false;
					}
				}
			}
			else if(type=='message_quick'){
				var location = window.location;
				if(current_location==location){
					if(document.getElementById('quick_post_article_button')!=undefined){
						document.getElementById('quick_post_article_button').disabled = false;
					}
				}
			}	
		}
	});
	
}


function getCurrentChart(){
	
	if($('#all').css('display') == 'block'){
		return 'all';
	}else if($('#positive').css('display') == 'block'){
		return 'positive';
	}else if($('#negative').css('display') == 'block'){
		return 'negative';
	}else{
		return 'all';
	}
	
	
}



function getAjaxUploadProcessor(path){
	ajaxProcessor = new AjaxUpload('#id_file', {
		  action: path,
		  name: 'file',
		  data: {
		    list : $('#id_list').attr('value')
		  },
		  autoSubmit: true,
		  onChange: function(file, extension){
			  $("#upload_loading").fadeIn('slow');
			  if (extension != 'csv'){
	              // extension is not allowed
	              jQuery.facebox('<div class="content" color="red"><div class="cb1"><div class="fieldLabel">Error: invalid file extension</div><div class="clearFloat"></div></div></div>');
	              // cancel upload
	              $("#upload_loading").fadeOut('slow');
	              return false;
	           }
		  },
		  onSubmit: function(file, extension) {
			  
	      },
		  onComplete: function(file, response) {
	    	  $("#upload_loading").fadeOut('slow');
	    	  $("#upload_state").append('<div>Submission of file "'+file+'" '+response+"!</div>");
	    	  }
		});
	
}


function check_b4_submit(action){
	$.ajax({
		url: action,
		type: 'POST',
		data: {},
		timeout:GLOBAL_TIMEOUT,
		success: function(data, textStatus){
			if(action == '/post/rule/article/quickcheck/'){
				$("option",$("#id_channels")).remove();
				$("option",$("#id_fchannels")).remove();
				
				data = eval(data);
				twitter = data[0];
				facebook = data[1];
				for(var i=0;i<twitter.length;i++){
					$("#id_channels").append('<option value="'+twitter[i][0]+'">'+twitter[i][1]+'</option>');
				}
				for(var i=0;i<facebook.length;i++){
					$("#id_fchannels").append('<option value="'+facebook[i][0]+'">'+facebook[i][1]+'</option>');
				}
				if(twitter.length==0 && facebook.length==0){
					$('#post_message_box').empty();
					$('#post_message_box').append('\
							<div>\
						    <div class="fieldDetail">you must add at least one account!</div>\
						    <div class="clearFloat"></div>\
						    <div class="fieldDetail"><a href="/chan/twitter/login"> Go to add a Twitter account</a></div>\
						    <div class="fieldDetail"><a href="/chan/facebook/login"> Go to add a Facebook account</a></div>\
						    <div class="fieldDetail"><a href="/chan/fbpage/login"> Go to add a Facebook Page</a></div>\
						    <div class="clearFloat"></div>\
							</div>'
							
					
					
					);
				}
			}
			},
		error:function(xmlHttpRequest,error){
				$('#post_message_box').empty();
				$('#post_message_box').append(getErrorPage(error));
		   },
		complete:function(){
		   }
	 });
}

function updateTips(t) {
	$("#submit_state").empty();
	$('#submit_state').append(t);
	$('#submit_state').show();
}

function showPicDiv(){
	url = $('#fbPicture').val();
	if(url){
		$('img',$('#pic_detail')).attr('src', url);
		$('#pic_detail').show();
	}

}

function checkLength(o,n,min,max) {
	if ( o.val().length > max || o.val().length < min ) {
		updateTips("This field "+n+" is required.");
		o.addClass('validate-state-highlight');
		setTimeout(function() {
			o.removeClass('validate-state-highlight', 200);
		}, 500);
		return false;
	} else {
		return true;
	}

}

function checkEmpty(o, div){

	var checked = $('#'+div).attr('checked');
	if(!checked){
		return true;
	}
	if ( o.val()) {
		return true;
	}else{
		updateTips("you must choose an account!");
		o.addClass('validate-state-highlight');
		setTimeout(function() {
			o.removeClass('validate-state-highlight', 200);
		}, 500);
		return false;
	}
}

function checkCheckBoxEmpty(div, name){
	var flag = false;
	$('input', $('#'+div)).each(function(){
		if($(this).attr('checked')){
			flag = true;
		}
	});
	if(!flag){
		updateTips("you must choose a "+ name);
		$('#'+div).addClass('validate-state-highlight');
		setTimeout(function() {
			$('#'+div).removeClass('validate-state-highlight', 200);
		}, 500);
	}
	return flag;
}

function attach_link(type){
	
	var checked =  $(type).is(':checked');
	
	if(checked){
		fetch_link();	
	}else{
		$('input',$('#link_detail')).val(null);
		image_links=null;
		
		$('#id_pic_info_current').text(1);
		$('#id_pic_info_total').text(0);
		$('#link_detail').hide();
		$('#picture_info').empty();
		$('#id_fbPicture').val(null);
		$('#id_fbDescription').val('');
		$('#id_fbName').val('');
	}
}

function fetch_link(){
	image_links = null;
	var link = $('#id_url').val();
	data = {link:link};
	var title = '';
	var description = '';
	$('#link_detail_loading').show();
	$.ajax({
		url: '/post/rule/article/getLink/',
		type: 'POST',
		data: data,
		timeout:GLOBAL_TIMEOUT,
		success: function(data, textStatus){
			data = eval(data);
			title = data[0];
			description = data[1];
			image_links = data[2];
			$('#id_fbName').val(title);
			var maxCount=500;
			if (description.length > maxCount) {
				description = description.substring(0,maxCount);
			}
			$('#id_fbDescription').val(description);	

			var len=description.length;
			if(len!=0){
				var info_description=$('#id_info_description')
				info_description.empty();
				info_description.append(maxCount-len);
			}	
			$('#link_detail').show();
			if(image_links && image_links.length>0){
				img_preloadimg(image_links[0], 'picture_info');
				$('#id_pic_info_current').text(1);
				$('#id_fbPicture_current').val(String(1));
				$('#id_pic_info_total').text(image_links.length);
				$('#id_fbPicture_total').val(String(image_links.length));
				$('#id_fbPicture').val(image_links[0]);
				if($('#thumbnail').attr('checked')){
					$('#id_fbPicture').val(image_links[0]);
				}
				$('#picture_info_control').show();
			}else{
				$('#picture_info_control').hide();
				$('#id_pic_info_current').text(1);
				$('#id_pic_info_total').text(0);
				$('#picture_info').empty();
				$('#picture_info').append('<span class="img_loding">No Thumbnail!</span>');
				$('#id_fbPicture').val(null);
			}
				
		   },
		error:function(xmlHttpRequest,error){
			   	title ='';
			   	description = '';
			   	image_links = null;
			   	$('#picture_info_control').hide();
				$('#id_pic_info_current').text(1);
				$('#id_pic_info_total').text(0);
				$('#picture_info').empty();
				$('#picture_info').append('<span class="img_loding">No Thumbnail!</span>');
				$('#id_fbPicture').val(null);
		   },
		complete:function(){
		   $('#link_detail_loading').hide();
			$('#id_fbName').val(title);
			$('#id_fbDescription').val(description);			
			$('#link_attchment').show();
		}
	 });

}

function preview(){

	var total = $('#id_pic_info_total').text();
	var index = $('#id_pic_info_current').text();
	
    if(!index){
    	index = 1;
    }
    
    total = parseInt(total);
	index = parseInt(index);
	
	if(index > image_links.length){
		index = image_links.length;
	}
	if(index <= 1){
		return false;
	}
	img_preloadimg(image_links[index-2],'picture_info');
	$('#id_pic_info_current').text(index-1);
	$('#id_fbPicture_current').val(index-1);
}

function next(){
	
	var total = $('#id_pic_info_total').text();
	var index = $('#id_pic_info_current').text();
	
	if(!index){
    	index = 1;
    }
	
	total = parseInt(total);
	index = parseInt(index);
	
    
	if(index >= image_links.length){
		return false;
	}
	if(index < 1){
		index = 1;
	}
	
	img_preloadimg(image_links[index],'picture_info');
	$('#id_pic_info_current').text(index+1);
	$('#id_fbPicture_current').val(index+1);
}


function shift_link(url){
	if(url.value != ''){
		$('#is_attach').attr('checked', false);
		image_links = null;
		
		$('#id_pic_info_current').text(1);
		$('#id_pic_info_total').text(0);
		$('input',$('#link_detail')).val(null);
		$('#link_detail').hide();
		
		if(!$(url).val() && $('#id_type').val() && $('#id_type').val() > 0){
			$('input', $('#link_attchment')).val(null);
			$('img', $('#link_attchment')).attr('src',null);
			$('#link_attchment').hide();
			
		}else{
			$('#link_attchment').show();
		}
	}	
}

function shift_pic(input){
	
	var ischecked = $(input).attr('checked');
	if(!ischecked){
		$('#picture_info').empty();
		$('#picture_info').append('<span class="img_loding">No Thumbnail!</span>');
		$('#picture_info_control').hide();
		$('#id_fbPicture').val(null);
	}else{
		$('#picture_info').show();
		
		var total = $('#id_pic_info_total').text();
		total = parseInt(total);
		if(total > 0){
			$('#picture_info_control').show();
			
			var index = $('#id_pic_info_current').text();
			index = parseInt(index);
			
			$('#id_fbPicture').val(image_links[index-1]);
			
			img_preloadimg(image_links[index-1],'picture_info');
			
		}else{
			$('#picture_info_control').hide();
			
			$('#picture_info').empty();
			$('#picture_info').append('<span class="img_loding">No Thumbnail!</span>');
			
			$('#id_fbPicture').val(null);
		}
	}
	
}

function refreshFanPage(id){
    time = Math.round(Math.random()*10000)
    window.location.href = '/#/chan/fanpage/refresh/?id='+id+'&time='+time
}

function refreshGroup(id){
	time = Math.round(Math.random()*10000)
    window.location.href = '/#/chan/groupmember/refresh/?id='+id+'&time='+time
}


function choosePostTypeCampaign(type){
	document.getElementById('channel_info_campaign_error').style.display = 'none';
	document.getElementById('fchannel_info_campaign_error').style.display = 'none';
	var id = type.id;
	var checked = type.checked;
	if (!checked){
		if(id == 'is_twitter_campaign'){
			document.getElementById('channel_info_campaign').style.display = 'none';
			$('#channels_campaign').val(null);
			// document.getElementById('t_info').style.display="none";
		} 
		else if(id == 'is_facebook_campaign'){
			document.getElementById('fchannel_info_campaign').style.display = 'none';
			$('#fchannels_campaign').val(null);
			document.getElementById('f_info').style.display="none"; 
		}
	}else { 
		if(id == 'is_twitter_campaign'){
			document.getElementById('channel_info_campaign').style.display = '';
			if(document.getElementById('twitter_count').value=='1'){
				document.getElementById('channels_campaign').options[0].selected=true;
			}
		} 
		else if(id == 'is_facebook_campaign'){
			document.getElementById('fchannel_info_campaign').style.display = '';
			if(document.getElementById('facebook_count').value=='1'){
				document.getElementById('fchannels_campaign').options[0].selected=true;
			}
		}
	} 
}

function choosePostTypeCampaignQuickPost(type){
	document.getElementById('channel_info_campaign_error').style.display = 'none';
	document.getElementById('fchannel_info_campaign_error').style.display = 'none';
	var id = type.id;
	var checked = type.checked;
	if (!checked){
		if(id == 'is_twitter_campaign'){
			document.getElementById('channel_info_campaign').style.display = 'none';
			$('#id_channels').val(null);
		} 
		else if(id == 'is_facebook_campaign'){
			document.getElementById('fchannel_info_campaign').style.display = 'none';
			$('#id_fbDestinations').val(null);
		}
	}else { 
		if(id == 'is_twitter_campaign'){
			document.getElementById('channel_info_campaign').style.display = '';
			if(document.getElementById('twitter_count').value=='1'){
				document.getElementById('id_channels').options[0].selected=true;
			}
		} 
		else if(id == 'is_facebook_campaign'){
			document.getElementById('fchannel_info_campaign').style.display = '';
			if(document.getElementById('facebook_count').value=='1'){
				document.getElementById('id_fbDestinations').options[0].selected=true;
			}
		}
	} 
}

function ajaxFormSubmitCampaignFeedQuick(ret_url,form){
	var current_location = window.location;
	document.getElementById('quick_post_feed_button').disabled = true;
	document.getElementById('channel_info_campaign_error').style.display = 'none';
	document.getElementById('fchannel_info_campaign_error').style.display = 'none';
	var tag = true;
	if(document.getElementById('is_twitter_campaign')!=null){
		var twitter = document.getElementById('is_twitter_campaign').checked;
		if(twitter){
			var	twitter_accounts = $('#id_channels');
			if(!twitter_accounts.val()){
				document.getElementById('channel_info_campaign_error').style.display = '';
				document.getElementById('quick_post_feed_button').disabled = false;
				tag = false;
			}
		}
	}
	if(document.getElementById('is_facebook_campaign')!=null){
		var facebook = document.getElementById('is_facebook_campaign').checked;
		if(facebook){
			var	fchannels_accounts = $('#id_fbDestinations');
			if(!fchannels_accounts.val()){
				document.getElementById('fchannel_info_campaign_error').style.display = '';
				document.getElementById('quick_post_feed_button').disabled = false;
				tag = false;
			}
		}
	}
	if(tag){
		ret_url=document.getElementById('ret_url_quickpost').value;
		ret_url=ret_url.replace(/andmarkreplace/g,'&');
		ajaxFormSubmit(ret_url,form,current_location,'feed_quick');
	}
}

function chooseCampaignOnlyTitleCheck(type){
	var facebook = document.getElementById('is_facebook_campaign').checked;
	var checked = type.checked;
	if (facebook){
		if (!checked){		
			document.getElementById('f_info').style.display=""; 
		}
		else { 
			document.getElementById('f_info').style.display = 'none';
		} 	
	}
}

function chooseFacebookPostType(type){
	var value = type.value;
	document.getElementById('fbPostStyleSelect').value=value; 
}

function affixSubmit(){
	var affix_ready=true;
	document.getElementById('prefix_title_input_error').style.display=='none';
	document.getElementById('suffix_title_input_error').style.display=='none';
	document.getElementById('prefix_title_input_error_duplicate').style.display=='none';
	document.getElementById('suffix_title_input_error_duplicate').style.display=='none';	
	if(document.getElementById('prefix_title_detail')!=null){	
		if(!document.getElementById('prefixTitle_id').checked){
			document.getElementById('prefixDelimter').value='';
		}
		else{
		 	if(document.getElementById('prefix_title_input_info').style.display==''){
		 		var input_symbol=document.getElementById('prefix_title_input').value;
		 		if(input_symbol!=''){
		 			if(input_symbol.length>1){
		 				affix_ready=false;
		 				document.getElementById('prefix_title_input_error').style.display='';
		 			}
		 			else{
		 				var prefixes_element=document.getElementById('prefixDelimter');
		 				if(!checkAffixesDuplicate('prefix',input_symbol,prefixes_element)){
		 					affix_ready=false;
		 				}
		 				else{
		 					if(!input_symbol==document.getElementById('prefix_title_input_hidden').value){
		 						affixesCheck(true,'prefix_title_input',prefixes_element);		 
		 					}				
		 				}
		 			}
		 		}
		 	}
		}
	}
	if(document.getElementById('suffix_title_detail')!=null){
		if(!document.getElementById('suffixTitle_id').checked){
			document.getElementById('suffixDelimter').value='';
		}
		else{
		 	if(document.getElementById('suffix_title_input_info').style.display==''){
		 		var input_symbol=document.getElementById('suffix_title_input').value;
		 		if(input_symbol!=''){
		 			if(input_symbol.length>1){
		 				affix_ready=false;
		 				document.getElementById('suffix_title_input_error').style.display='';
		 			}
		 			else{
		 				var suffixes_element=document.getElementById('suffixDelimter');
						if(!checkAffixesDuplicate('suffix',input_symbol,suffixes_element)){
		 					affix_ready=false;
		 				}
		 				else{
		 					if(!input_symbol==document.getElementById('suffix_title_input_hidden').value){		 				
		 						affixesCheck(true,'suffix_title_input',suffixes_element);		 
		 					}				
		 				}
		 			}
		 		}
		 	}
		}
	}
	return affix_ready;
}

function ajaxFormSubmitCampaign(ret_url,form){
	var current_location = window.location;
	document.getElementById('channel_info_campaign_error').style.display = 'none';
	document.getElementById('fchannel_info_campaign_error').style.display = 'none';
	var tag = true;
	if(document.getElementById('is_twitter_campaign')!=null){
		var twitter = document.getElementById('is_twitter_campaign').checked;
		if(twitter){
			var	twitter_accounts = document.getElementById('channels_campaign');
			if(!twitter_accounts.value){
				document.getElementById('channel_info_campaign_error').style.display = '';
				tag = false;
			}
		}
	}
	if(document.getElementById('is_facebook_campaign')!=null){
		var facebook = document.getElementById('is_facebook_campaign').checked;
		if(facebook){
			var	fchannels_accounts = document.getElementById('fchannels_campaign');
			if(!fchannels_accounts.value){
				document.getElementById('fchannel_info_campaign_error').style.display = '';
				tag = false;
			}
		}
	}
	if (ret_url.indexOf('/post/rule/feed/')!= -1)
	{
		var affix_ready=affixSubmit();
	}
	else {
		var affix_ready = true
	}
	if(affix_ready&&tag){	
		ajaxFormSubmit(ret_url,form,current_location,'message_feed_campaign');		
	}
}

function img_preloadimg(url,div){
	var img=new Image();
	
	$('#'+div).empty();
	$('#'+div).append('<span class="img_loding">loading...</span>');
	
	img.onload=function(){
		$('#'+div).empty();
		$('#'+div).append('&nbsp;<img width="180px;" src="'+url+'" class="cursorPointer" border="0">');};
	img.onerror=function(){
		$('#'+div).empty();
		$('#'+div).append('<span class="img_loding">Bad Thumbnail!</span>');
			};
	img.src=url;
	$('#id_fbPicture').val(url);
	}

function ajaxFormSubmitQuick(ret_url, form){
	document.getElementById('quick_post_article_button').disabled = true;
	var is_twitter = $('option[value=0]','#id_type').attr('selected');
	var is_facebook = $('option[value=1]','#id_type').attr('selected');
	
	var current_location = window.location;
	
	$('#id_channels_errorlist').hide();
	$('#id_fbDestinations_errorlist').hide();
	var tag = true;
	if(is_twitter){
		var	twitter_accounts = $('#id_channels').val();
		if(!twitter_accounts){
			$('#id_channels_errorlist').show();
			document.getElementById('quick_post_article_button').disabled = false;
			tag = false;
		}
	}
	if(is_facebook){
		var	fchannels_accounts = $('#id_fbDestinations').val();
		if(!fchannels_accounts){
			$('#id_fbDestinations_errorlist').show();
			document.getElementById('quick_post_article_button').disabled = false;
			tag = false;
		}
	}
	if(tag){
		ret_url=document.getElementById('ret_url_quickpost').value;
		ret_url=ret_url.replace(/andmarkreplace/g,'&');
		ajaxFormSubmit(ret_url,form,current_location,'message_quick');
	}

};

function post_a_message(){
	var ret_url = String(window.location);	
	if(ret_url.indexOf('#')!=-1){
		var url_list = ret_url.split("#");
		ret_url=url_list[1];
	}
	else{
		ret_url='/';
	}
	ret_url=ret_url.replace(/&/g,'andmarkreplace');
	window.location = '#/post/rule/article/quickcreate/?ret_url='+escape(ret_url);
}

function post_a_feed(){
	var ret_url = String(window.location);	
	if(ret_url.indexOf('#')!=-1){
		var url_list = ret_url.split("#");
		ret_url=url_list[1];
	}
	else{
		ret_url='/';
	}
	
	ret_url=ret_url.replace(/&/g,'andmarkreplace');
	window.location = '#/post/rule/feed/quickcreate/?ret_url='+escape(ret_url);
}

function dashboardViewRankingDetail(){
	var timeRange=document.getElementById('timeRangeRanking').value;
	var url='#/graph/clickranking?timeRange='+timeRange;
	window.location=url;
}

function dashboardViewChartDetail(){
	var timeRange=document.getElementById('timeRange').value;
	var url='#/graph/chart?timeRange='+timeRange;
	window.location=url;
}

function ajaxFormSubmitCustom(ret_url,form,start_number,string_id,type){
	document.getElementById('rule_name_error_duplicate').style.display='none';
	var tag=getShortLinks(start_number,string_id,type);
	if(tag){
		var current_location = window.location;
		ajaxFormSubmit(ret_url,form,current_location,'custom_campaign');	
	}	
}
function AddFbApp(key){
   var id = document.getElementById('apps').value;
   page_url = '/chan/fbapp/confirm?id='+id+'&key='+key
   window.location=page_url;
}

function AddFbPage(url){
   var id = document.getElementById('fchannels').value;
   page_url = '/#/' + url + '?id=' + id
   window.location=page_url;
}

function fanPageChangeAcc(id){
	location.href ='/#/chan/fanpage/?id='+id ;
	document.getElementById('conversation_submenu').style.display='none';
}

function MemberGroupChangeAcc(id){
	location.href ='/#/chan/groupmember/?id='+id ;
	document.getElementById('conversation_submenu').style.display='none';
}

function changePageShow(check){
   var id = document.getElementById('id').value;
   if (check.checked){
      show = 'yes'
   }
   else {
      show = 'no'
   }
   location.href ='/#/chan/fanpage/?id='+id+'&show='+show
}

function changeGroupShow(check){
var id = document.getElementById('id').value;
   if (check.checked){
      show = 'yes'
   }
   else {
      show = 'no'
   }
   location.href ='/#/chan/groupmember/?id='+id+'&show='+show

}

function changeSystemMonitor(type)
{
	jQuery.get('/log/monitor/change/', {type:type},function(data){
	    var result = data 
	    msgId = type+'Msg'
	    actionId = type+'Action'
	    if (result=='True'){
	       document.getElementById(msgId).innerHTML = "Active"
	       document.getElementById(actionId).value = "Suspend"
	    }
	    else{
	       document.getElementById(msgId).innerHTML = "Inactive"
	       document.getElementById(actionId).value = "Resume"
	    }
	});
}

function chooseTheFchannel(form){
   var id = form.value
   var src = document.getElementById(id).value
   document.getElementById('choice_img').src = src

}

function chooseCustomFeed(fsid){
	location.href = '/#/rssfeed/custom/?fsid=' + fsid.value
}

function getFooterText(url){
	jQuery.get('/usr/islogin/', function(data) { 
	     var a = data
	     if (a=='1'){
	     window.location = '/#'+url
	     } 
	     else {
	     window.location = url
	     }
		})
}

function verifyLink(){
	document.getElementById('verify_error_msg').style.display='none';
	var link=document.getElementById('short_link_url').value;
	if(link==''){
		document.getElementById('verify_error_msg').innerHTML='Need a link';
		document.getElementById('verify_error_msg').style.display='';
	}
	else{
		jQuery.get('/link/url/title/?link='+link, function(data) { 
	    	var response=eval("("+data+")");  
	    	if(response['state']=='success'){
	    		document.getElementById('verify_link').style.display='none';
	    		document.getElementById('checked_link').style.display='';
	    		document.getElementById('short_link_title').value=response['title'];
	    		document.getElementById('title_div').style.display='';
	    	}
	    	else{
	    		document.getElementById('verify_error_msg').innerHTML=response['error'];
				document.getElementById('verify_error_msg').style.display='';
	    	}
		})
	}
}

function verifyLinkCustom(number,media_url){
	document.getElementById('verify_error_blank_number_'+number).style.display='none';
	document.getElementById('verify_error_invalid_number_'+number).style.display='none';
	document.getElementById('verify_error_add_new_number_'+number).style.display='none';
	var link=document.getElementById('short_link_url_number_'+number).value;
	if(link==''){
		document.getElementById('verify_error_blank_number_'+number).style.display='';
	}
	else{
		jQuery.get('/link/url/title/?link='+link, function(data) { 
	    	var response=eval("("+data+")");  
	    	if(response['state']=='success'){
	    		document.getElementById('verify_link_number_'+number).style.display='none';
	    		document.getElementById('checked_link_number_'+number).style.display='';
	    		document.getElementById('short_link_title_number_'+number).value=response['title'];
	    		document.getElementById('title_div_number_'+number).style.display='';
	    		document.getElementById('delete_link_number_'+number).style.display='';
				document.getElementById('short_link_url_number_'+number).style.display='none';
								
				newNode=document.createElement("span"); 
				newNode.setAttribute("id","short_link_url_label_number_"+number);
				newNode.innerHTML="<label autosize='false' class='fieldLabel' width='300px'><a target='_blank' class='cursorPointer' href='"+document.getElementById('short_link_url_number_'+number).value+"'>"+document.getElementById('short_link_url_number_'+number).value+'</label>';
				document.getElementById("verify_link_input_number_"+number).appendChild(newNode);		
				
				addNewShortLink(media_url);		
			}
	    	else{
				document.getElementById('verify_error_invalid_number_'+number).style.display='';
	    	}
		})
	}
}

function ajaxFormSubmitLink(form){
	if(document.getElementById('checked_link').style.display!=''){
		document.getElementById('verify_error_msg').style.display='none';
		var link=document.getElementById('short_link_url').value;
		if(link==''){
			document.getElementById('verify_error_msg').innerHTML='Need a link';
		}
		else{
			document.getElementById('verify_error_msg').innerHTML='Verify before submit';
		}
		document.getElementById('verify_error_msg').style.display='';
	}
	else{
		var current_location = window.location;
		makeFormAjaxSubmit(form);
	}		
}

function ajaxFormTwitterCallbackSubmit(form){
	var current_location = window.location;
	ajaxFormSubmit('/#/chan/',form,current_location,'twitter_callback_like');	
}

function ajaxFormFacebookCallbackSubmit(form){
	var current_location = window.location;
	ajaxFormSubmit('/#/chan/fchannel/',form,current_location,'facebook_callback_account');	
}

function ajaxFormFacebookPageCallbackSubmit(form,other_ids){
	var ids='';
	for(var i=0;;i++){
		var check=document.getElementById('pchannel_post_check_'+String(i));
		if(check!=null){
			if(check.checked){
				if(ids==''){
					ids=document.getElementById('pchannel_post_id_'+String(i)).value;
				}
				else{
					ids=ids+'SubstitutePChannel'+document.getElementById('pchannel_post_id_'+String(i)).value;
				}
			}
		}
		else break
	}
	document.getElementById('post_fb_ids').value=ids;
	
	var current_location = window.location;
	ajaxFormSubmit('/#/chan/fbpage/',form,current_location,'facebook_callback_page');	
}

function tryclick(){
var name=navigator.appName
if(name=="Microsoft Internet Explorer")
	{
	document.getElementsByClassName('liketext').click()
	}
else
	{
	
	var a=document.createEvent("MouseEvents");
	a.initEvent("click", true, true); 
	var iObj = document.getElementsByClassName('fb_ltr')[0].contentDocument; 
	var like = iObj.getElementsByTagName('span')[0]
	like.dispatchEvent(a);
	}
}

function displayHtml5Define(){
	return true;
}

function getYLabelsCount(y_max){
	if(y_max<8){
		return 1;
	}
	else if(y_max>=8&&y_max<20){
		return 3;
	}
	else{
		return 5;
	}
}

function systemFetchTest(){
	url = document.getElementById('urlfetch-input').value
	jQuery.post("/log/urlfetch/test/",{url:url},
		  function(data){
		   alert(data)
		  });
}

function updateChannelCampaign(topicNumber){
	var keyword
	if(topicNumber==2){
		keyword = document.getElementById('firstTopic').value + '|' + document.getElementById('secondTopic').value
	} else{
		keyword = document.getElementById('firstTopic').value
	}
	var id = document.getElementById('channel-id').value
	
	jQuery.post("/mgmt/update_channel_campaign/", {id:id,keyword:keyword},
	  function(data){
	   if(data=='success'){
	   	window.location.href="/#/chan/"
	   }else{
	   	alert('failure')
	   }
	  });

}

function syncContentChannel(id){
	jQuery.post("/mgmt/sync/",{'id':id},
		  function(data){
		   jQuery.facebox.close();
		  });
}

function syncAdvancedDM(id){
	jQuery.post("/dm/rule/advanced/sync/",{'id':id},
		  function(data){
		   jQuery.facebox.close();
		  });
}

function choosefilterType(ele){
	type = ele.value
	if (type==0){
		document.getElementById('filter-keywords').style.display = "none"
		document.getElementById('user-included').style.display = "none"
		document.getElementById('user-excluded').style.display = ""
	}else if (type==1){
		document.getElementById('filter-keywords').style.display = "none"
		document.getElementById('user-included').style.display = ""
		document.getElementById('user-excluded').style.display = "none"
	}else if (type==2){
		document.getElementById('filter-keywords').style.display = ""
		document.getElementById('user-included').style.display = "none"
		document.getElementById('user-excluded').style.display = "none"
	}
}

function setUserTag(id){
	var tag = document.getElementById('user-tag').value
	jQuery.post("/usr/tag/",{'id':id,'tag':tag},
		  function(data){
		    jQuery.facebox.close();
		    var tag_id = 'tag_' + id
		    document.getElementById(tag_id).innerHTML = data
		  });
}

function realtimePost(){
	jQuery.get("/log/realtime/post/",
		  function(data){
		   alert(data)
		  });
}

function refreshChannelStatsChart() {
	if (document.getElementById('check-post').checked) {
		var dataPost = eval($('#data-post').val());
		var tipPost = eval($('#tip-post').val());
	} else {
		var dataPost = new Array();
		var tipPost = new Array();
	}
	if (document.getElementById('check-click').checked) {
		var dataClick = eval($('#data-click').val());
		var tipClick = eval($('#tip-click').val());
	} else {
		var dataClick = new Array();
		var tipClick = new Array();
	}		
	if (document.getElementById('check-follower').checked) {
		var dataFollower = eval($('#data-follower').val());
		var tipFollower = eval($('#tip-follower').val());
	} else {
		var dataFollower = new Array();
		var tipFollower = new Array();
	}
	if (document.getElementById('check-klout').checked) {
		var dataKlout = eval($('#data-klout').val());
		var tipKlout = eval($('#tip-klout').val());
	} else {
		var dataKlout = new Array();
		var tipKlout = new Array();
	}
	if (document.getElementById('check-search-rank').checked) {
		var dataSearchRank = eval($('#data-search-rank').val());
		var tipSearchRank = eval($('#tip-search-rank').val());
	} else {
		var dataSearchRank = new Array();
		var tipSearchRank = new Array();
	}
	if (document.getElementById('check-retweet').checked) {
		var dataRetweet = eval($('#data-retweet').val());
		var tipRetweet = eval($('#tip-retweet').val());
	} else {
		var dataRetweet = new Array();
		var tipRetweet = new Array();
	}
	if (document.getElementById('check-mention').checked) {
		var dataMention = eval($('#data-mention').val());
		var tipMention = eval($('#tip-mention').val());
	} else {
		var dataMention = new Array();
		var tipMention = new Array();
	}
	var tooltips = (new Array()).append(tipPost).append(tipClick).append(tipFollower).append(tipKlout).append(tipSearchRank).append(tipRetweet).append(tipMention);
	RGraph.Clear(document.getElementById("myLine"));
	var labels = eval($('#labels').val());
	for (var i = 0; i < labels.length; i++) {
		if ((i % 3 != 0) && (i != labels.length - 1))
			labels[i] = '';
	}
	var line = new RGraph.Line("myLine", dataPost, dataClick, dataFollower, dataKlout, dataSearchRank, dataRetweet, dataMention);
	line.Set('chart.linewidth', 2);
	line.Set('chart.hmargin', 5);
	line.Set('chart.key', ['Posts', 'Clicks', 'Followers', 'Klouts', 'Search Ranks', 'Retweets', 'Mentions']);
	line.Set('chart.tooltips', tooltips);
	line.Set('chart.key.position', 'gutter');
	line.Set('chart.tickmarks', 'filledcircle');
	line.Set('chart.ticksize', 5);
	line.Set('chart.labels', labels);
	line.Set('chart.gutter', 50);
	line.Draw();
}

function refreshSysChart() {
	if (document.getElementById('check-cmpclicks').checked) {
		var dataCmpClicks = eval($('#data-cmpclicks').val());
		var tipCmpClicks = eval($('#tip-cmpclicks').val());
	} else {
		var dataCmpClicks = new Array();
		var tipCmpClicks = new Array();
	}
	if (document.getElementById('check-cmpposts').checked) {
		var dataCmpPosts = eval($('#data-cmpposts').val());
		var tipCmpPosts = eval($('#tip-cmpposts').val());
	} else {
		var dataCmpPosts = new Array();
		var tipCmpPosts = new Array();
	}
	if (document.getElementById('check-cmpurls').checked) {
		var dataCmpUrls = eval($('#data-cmpurls').val());
		var tipCmpUrls = eval($('#tip-cmpurls').val());
	} else {
		var dataCmpUrls = new Array();
		var tipCmpUrls = new Array();
	}
	if (document.getElementById('check-cmpfollowers').checked) {
		var dataCmpFollowers = eval($('#data-cmpfollowers').val());
		var tipCmpFollowers = eval($('#tip-cmpfollowers').val());
	} else {
		var dataCmpFollowers = new Array();
		var tipCmpFollowers = new Array();
	}
	if (document.getElementById('check-cmpaccounts').checked) {
		var dataCmpAccounts = eval($('#data-cmpaccounts').val());
		var tipCmpAccounts = eval($('#tip-cmpaccounts').val());
	} else {
		var dataCmpAccounts = new Array();
		var tipCmpAccounts = new Array();
	}
	var labels = eval($('#label').val());
	for (var i = 0; i < labels.length; i++) {
		if ((i % 3 != 0) && (i != labels.length - 1))
			labels[i] = '';
	}
	RGraph.Clear(document.getElementById("myLine"));
	var line = new RGraph.Line("myLine", 
		dataCmpClicks,
		dataCmpPosts,
		dataCmpUrls,
		dataCmpFollowers,
		dataCmpAccounts);
	var tooltips = (new Array()).append(tipCmpClicks).append(tipCmpPosts).append(tipCmpUrls).append(tipCmpFollowers).append(tipCmpAccounts);
	line.Set('chart.labels', labels);
	line.Set('chart.tooltips', tooltips);
	line.Set('chart.key', ['Clicks', 'Posts', 'URLs', 'Followers', 'Accounts']);
	line.Set('chart.key.position', 'gutter');
	line.Set('chart.colors', ['#f90','#f0f','#0ff','#39f','#9f3']);
	line.Set('chart.linewidth', 2);
	line.Set('chart.hmargin', 5);
	line.Set('chart.tickmarks', 'filledcircle');
	line.Set('chart.ticksize', 5);
	line.Set('chart.gutter', 50);
	line.Draw();
}


function refreshContentSourceChart() {
	if (document.getElementById('check-posts').checked) {
		var dataPosts = eval($('#data-posts').val());
		var tipPosts = eval($('#tip-posts').val());
	} else {
		var dataPosts = new Array();
		var tipPosts = new Array();
	}
	if (document.getElementById('check-clicks').checked) {
		var dataClicks = eval($('#data-clicks').val());
		var tipClicks = eval($('#tip-clicks').val());
	} else {
		var dataClicks = new Array();
		var tipClicks = new Array();
	}		
	var tooltips = (new Array()).append(tipPosts).append(tipClicks)
	RGraph.Clear(document.getElementById("myLine"));
	var labels = eval($('#labels').val());
	for (var i = 0; i < labels.length; i++) {
		if ((i % 3 != 0) && (i != labels.length - 1))
			labels[i] = '';
	}
	var line = new RGraph.Line("myLine", dataPosts, dataClicks);
	line.Set('chart.linewidth', 2);
	line.Set('chart.hmargin', 5);
	line.Set('chart.key', ['Posts', 'Clicks']);
	line.Set('chart.tooltips', tooltips);
	line.Set('chart.key.position', 'gutter');
	line.Set('chart.tickmarks', 'filledcircle');
	line.Set('chart.ticksize', 5);
	line.Set('chart.labels', labels);
	line.Set('chart.gutter', 50);
	line.Draw();
}


function changePaginate(orginUrl, select) {
	var newVal = select.value;
	var parts = orginUrl.split('&');
	for (var i = 0; i < parts.length; i++) {
		if (parts[i].indexOf('paginate_by=') >= 0) {
			parts[i] = parts[i].substring(0, parts[i].indexOf('=') + 1) + newVal;
		}
	}
	var newUrl = parts.join('&');
	window.location.href = newUrl;
}

function topicAutoComplete(selector, topics) {
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
}

function topicCampActivation(id){
	jQuery.get("/mgmt/topic/activate/?id="+id,
		  function(data){
		   if (data=='0'){
		    document.getElementById('img_deactivate_'+id).style.display = "none"
			document.getElementById('img_activate_'+id).style.display = ""
		   }else {
		    document.getElementById('img_deactivate_'+id).style.display = ""
			document.getElementById('img_activate_'+id).style.display = "none"
		   }
		  });
}

function chooseNoChannelPriority(priority){
	var priority = priority.value
	var pagination = document.getElementById('pagination').value
	window.location.href = "/#/mgmt/topic/nochannel/?priority="+priority+'&pagination='+pagination

}

function chooseNoChannelPagination(pagination){
	var priority = document.getElementById('priority').value
	var pagination = pagination.value
	window.location.href = "/#/mgmt/topic/nochannel/?priority="+priority+'&pagination='+pagination

}

function chooseNoTopicPagination(pagination){
	var pagination = pagination.value
	window.location.href = "/#/mgmt/topic/notopic/?pagination="+pagination

}

function updateNoChannelPriority(id){
	var priority = document.getElementById(id).value
	jQuery.get("/mgmt/topic/nochannel/update/", { id: id,priority:priority });
}

function dealStatsSort(){
	var orderBy = document.getElementById('orderBy').value 
	var cat = document.getElementById('cat').value 
	var location = document.getElementById('location').value 
	var pagination = document.getElementById('pagination').value 
	window.location.href = "/#/deal/stats/?orderBy=" +orderBy + "&cat="+cat+"&location=" + location + "&pagination=" + pagination
}
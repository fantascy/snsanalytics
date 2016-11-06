
var ContactThankYouMsg = "Your message has been sent. Thank you!";	// The message shown after send

// initialize form validation
// -------------------------------------------------------------------
jQuery(document).ready(function($){
	$("#CommentForm").validate({ 
		submitHandler:function(form){
			ajaxContact(form); return false;
		}
	});
});

// Ajax send email submit contact form
// -------------------------------------------------------------------
function ajaxContact(theForm) {
	
	jQuery('#loader').fadeIn();
	var formData = jQuery(theForm).serialize(), note = jQuery('#Note');
	
	jQuery.ajax({
		type:"POST",url:"contact-send.php",data:formData,success:function(response){if(note.height()){note.fadeIn("fast",function(){jQuery(this).hide();});}else{note.hide();}jQuery("#LoadingGraphic").fadeOut("fast",function(){if(response.indexOf("success")!=-1){if(jQuery.browser.msie&&parseInt(jQuery.browser.version,10)<=8){jQuery(theForm).css("display","none");}else{jQuery(theForm).animate({opacity:0},"fast",function(){jQuery(this).addClass("hidden");});}}result="";c="";if(response==="success"){result=ContactThankYouMsg;c="success";}else{result=response;c="error";}note.removeClass("success").removeClass("error").text("");var i=setInterval(function(){if(!note.is(":visible")){note.html(result).addClass(c).slideDown("fast");clearInterval(i);}},40);});}
	});
	
	return false;
}

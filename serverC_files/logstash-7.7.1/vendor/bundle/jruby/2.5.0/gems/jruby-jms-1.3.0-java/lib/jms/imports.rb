# Import Java classes into JMS Namespace
module JMS
  java_import 'javax.jms.DeliveryMode'
  java_import 'javax.jms.Message'
  java_import 'javax.jms.BytesMessage'
  java_import 'javax.jms.TextMessage'
  java_import 'javax.jms.MapMessage'
  java_import 'javax.jms.ObjectMessage'
  java_import 'javax.jms.StreamMessage'
  java_import 'javax.jms.Session'
  java_import 'javax.jms.Destination'
  java_import 'javax.jms.Queue'
  java_import 'javax.jms.Topic'
  java_import 'javax.jms.TemporaryQueue'
  java_import 'javax.jms.TemporaryTopic'
  java_import 'javax.jms.MessageConsumer'
  java_import 'javax.jms.MessageProducer'
  java_import 'javax.jms.QueueBrowser'
  java_import 'javax.jms.MessageListener'
  java_import 'javax.jms.ExceptionListener'
end